/** Rendered acceptance against an isolated real Python service (requires Playwright + Chromium).
 * CHUG_CHROMIUM_EXECUTABLE=/path/to/chrome node scripts/browser_integrated_review.cjs /tmp/evidence
 * Does not install dependencies, deploy, publish, or change normal user state.
 */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const {mkdtempSync,mkdirSync,writeFileSync,readFileSync}=require('node:fs');
const {tmpdir}=require('node:os');
const {resolve,join}=require('node:path');
const {createHash}=require('node:crypto');
const assert=require('node:assert/strict');
const net=require('node:net');
const root=resolve(__dirname,'..'), evidence=resolve(process.argv[2]||mkdtempSync(join(tmpdir(),'chug-rendered-')));
mkdirSync(evidence,{recursive:true});
const state=mkdtempSync(join(tmpdir(),'chug-browser-state-'));
const lib=join(root,'research/reference-library-v0.1');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const pause=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  const port=await new Promise(r=>{const s=net.createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>r(p))})});
  const base=`http://127.0.0.1:${port}`;
  let server,browser,page;
  const errors=[],checks=[],screenshots=[],writes=[];
  async function start(){
    server=spawn('python3',['-m','chug.server','--port',String(port),'--state-dir',state],{cwd:root});
    let log='';server.stderr.on('data',b=>log+=b);server.stdout.on('data',b=>log+=b);
    for(let i=0;i<100;i++){try{if((await fetch(base+'/api/queue')).ok)return}catch{}await pause(100)}
    throw new Error('Service did not start: '+log);
  }
  async function stop(){if(!server)return;const exited=new Promise(r=>server.once('exit',r));server.kill();await exited;server=null}
  async function shot(page,name){await page.screenshot({path:join(evidence,name+'.png'),fullPage:false});screenshots.push(name+'.png')}
  try{
    await start();
    browser=await chromium.launch({headless:true,executablePath:process.env.CHUG_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']});
    page=await browser.newPage({viewport:{width:1440,height:1000}});
    page.setDefaultTimeout(10000);
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(['error','warning'].includes(m.type()))errors.push(m.text())});
    page.on('response',r=>{if(r.request().method()==='POST')writes.push({url:new URL(r.url()).pathname,status:r.status()})});
    await page.goto(base);
    await page.locator('#queue button').first().waitFor({state:'attached'});
    assert.match(await page.title(),/Chug/);assert((await page.locator('#workspace').innerText()).length>100);
    checks.push('page identity, meaningful app content, no framework overlay');
    await page.getByRole('button',{name:'References',exact:true}).click();
    for(const file of ['references/nda/Mutual NDA - Product Evaluation - UK - v0.1.docx','references/sales-orders/Customer Order - Reseller Desktop Licences - v0.1.docx']){
      await page.locator('#reference-upload').setInputFiles(join(lib,file));
      const response=page.waitForResponse(r=>r.url().endsWith('/api/reference/upload')&&r.request().method()==='POST');
      await page.getByRole('button',{name:'Register standard',exact:true}).click();assert.equal((await response).status(),201);
      await page.locator('.reference-candidate').waitFor({state:'detached'});
    }
    checks.push('two controlled references uploaded and registered Active through browser');
    const files=['Incoming - Evaluation NDA with Longer Retention.docx','Incoming - Desktop Reseller Seat Increase.docx','Incoming - Ambiguous Reseller Cloud Scan Purchase.docx'];
    const response=page.waitForResponse(r=>r.url().endsWith('/api/intakes/batch'));
    await page.locator('#upload').setInputFiles(files.map(f=>join(lib,'incoming-tests',f)));
    const batch=await (await response).json();assert.equal(batch.counts.analysed,2);assert.equal(batch.counts.awaiting_reference,1);
    await page.locator('.batch-summary').waitFor();await shot(page,'desktop-batch');
    const detailFor=async name=>batch.items.find(i=>i.filename===name);
    const select=async name=>{const item=await detailFor(name);await page.locator(`#queue [data-id="${item.id}"]`).click();await page.locator('.doc-head h2').filter({hasText:name}).waitFor();return item};
    const nda=await select(files[0]);
    assert.equal(await page.locator('.finding-assessment-form').count(),4);
    assert.match(await page.locator('#workspace').innerText(),/provisional/);
    // Browser downloads must contain the exact original bytes, not reconstructed text.
    for(const [name,original] of [['Download exact incoming DOCX ↗',join(lib,'incoming-tests',files[0])],['Download exact reference DOCX ↗',join(lib,'references/nda/Mutual NDA - Product Evaluation - UK - v0.1.docx')]]){
      const download=page.waitForEvent('download');await page.getByRole('link',{name,exact:true}).click();
      assert.equal(hash(readFileSync(await (await download).path())),hash(readFileSync(original)));
    }
    let form=page.locator('.finding-assessment-form').last();
    await form.locator('[name=assessment]').selectOption('problem');await form.locator('[name=reason]').fill('Archive wording requires further discussion in this synthetic test.');await form.locator('[name=reviewer]').fill('Browser test reviewer');
    let saved=page.waitForResponse(r=>r.url().endsWith('/api/finding-assessments'));await form.getByRole('button',{name:'Save assessment'}).click();assert.equal((await saved).status(),201);
    await page.getByText('Latest:',{exact:false}).waitFor();
    let action=page.locator('.contract-action-form');await action.locator('[name=action]').selectOption('flag_for_review');await action.locator('[name=reviewer]').fill('Browser test reviewer');await action.locator('[name=rationale]').fill('Ask another reviewer to check the archive provision.');
    saved=page.waitForResponse(r=>r.url().endsWith('/api/contract-actions'));await action.getByRole('button',{name:'Record contract action'}).click();assert.equal((await saved).status(),201);
    await page.getByText('Contract action · flag for review',{exact:true}).waitFor();
    await page.getByRole('heading',{name:'Review history',exact:true}).scrollIntoViewIfNeeded();await shot(page,'desktop-saved-history');
    const before=await (await fetch(base+'/api/intakes/'+nda.sha256)).json();assert.equal(before.review_state,'flagged');assert.equal(before.human_decision.status,'pending');
    assert.equal(before.finding_assessments.length,1);
    // Confirm applicability separately after automatic analysis and assessment.
    const confirmation=page.locator('.intake-confirmation-form');await confirmation.locator('[name=reviewer]').fill('Browser test reviewer');await confirmation.locator('[name=rationale]').fill('Checked the evaluation purpose and mutual disclosure scope.');
    saved=page.waitForResponse(r=>r.url().endsWith('/reference-confirmation'));await confirmation.getByRole('button',{name:'Confirm reference applicability'}).click();assert.equal((await saved).status(),201);
    await page.getByRole('heading',{name:'Confirmed reference',exact:true}).waitFor();
    checks.push('NDA comparison -> original downloads -> finding assessment -> separate pending flag -> reference confirmation');
    const order=await select(files[1]);assert.equal(await page.locator('.finding-assessment-form').count(),2);
    assert.match(await page.locator('#workspace').innerText(),/Purchase of 60 desktop user subscriptions/);
    assert.match(await page.locator('#workspace').innerText(),/Purchase of 25 desktop user subscriptions/);
    form=page.locator('.finding-assessment-form').last();await form.locator('[name=assessment]').selectOption('needs_further_review');await form.locator('[name=reason]').fill('Confirm the customer seat requirement.');await form.locator('[name=reviewer]').fill('Browser test reviewer');
    saved=page.waitForResponse(r=>r.url().endsWith('/api/finding-assessments'));await form.getByRole('button',{name:'Save assessment'}).click();assert.equal((await saved).status(),201);
    await page.getByText('Latest:',{exact:false}).waitFor();
    await page.locator('.finding-review').last().scrollIntoViewIfNeeded();await shot(page,'desktop-order-review');
    const orderConfirmation=page.locator('.intake-confirmation-form');await orderConfirmation.locator('[name=reviewer]').fill('Browser test reviewer');await orderConfirmation.locator('[name=rationale]').fill('Checked reseller desktop scope against both exact originals.');
    saved=page.waitForResponse(r=>r.url().endsWith('/reference-confirmation'));await orderConfirmation.getByRole('button',{name:'Confirm reference applicability'}).click();assert.equal((await saved).status(),201);
    await page.getByRole('heading',{name:'Confirmed reference',exact:true}).waitFor();
    checks.push('customer-order automatic findings show both original/reference excerpts; assessment and separate applicability confirmation persist');
    await select(files[2]);assert.match(await page.locator('#workspace').innerText(),/Comparison not run/);assert.equal(await page.locator('.finding-assessment-form').count(),0);await shot(page,'desktop-abstention');
    // Deep link, keyboard activation and mobile rendering use the same real service.
    await page.setViewportSize({width:390,height:844});await page.reload();await page.locator('.doc-head').waitFor();
    assert(await page.locator('#workspace').isVisible());
    let overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
    if(overflow)throw new Error('Mobile page has horizontal overflow');
    await shot(page,'mobile-abstention');
    await page.getByRole('button',{name:'← Back to review queue',exact:true}).press('Enter');await page.locator('.queue-intro').waitFor();
    await page.locator(`#queue [data-id="${order.id}"]`).press('Enter');await page.locator('.finding-review').first().waitFor();
    await page.locator('.finding-review').last().scrollIntoViewIfNeeded();await shot(page,'mobile-order-review');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
    checks.push('390px mobile deep-link refresh, keyboard queue -> review navigation, no horizontal overflow');
    await stop();await start();await page.reload();await page.locator('.finding-review').first().waitFor();
    assert.match(await page.locator('#workspace').innerText(),/needs further review/);
    await page.goto(base+'/#intake/'+nda.sha256);await page.getByText('Contract action · flag for review',{exact:true}).waitFor();
    checks.push('cold service restart preserves browser-visible assessments, flag and reference confirmation');
    await page.setViewportSize({width:1440,height:1000});
    for(const [relative,family] of [['references/nda/Mutual NDA - Product Evaluation - UK - v0.1.docx','nda'],['references/sales-orders/Customer Order - Reseller Desktop Licences - v0.1.docx','customer_order']]){
      const path=join(lib,relative), upload=page.waitForResponse(r=>r.url().endsWith('/api/intakes')&&r.request().method()==='POST');
      await page.locator('#upload').setInputFiles(path);const exact=await (await upload).json();
      await page.locator('.doc-head h2').filter({hasText:path.split('/').at(-1)}).waitFor();
      assert.equal(exact.family,family);assert.equal(exact.human_decision.status,'pending');
      assert.equal(await page.locator('.finding-assessment-form').count(),0);
      assert.match(await page.locator('#workspace').innerText(),/No textual or structural differences/);
      if(family==='nda'){
        const download=page.waitForEvent('download');await page.getByRole('link',{name:'Download exact incoming DOCX ↗',exact:true}).click();
        assert.equal(hash(readFileSync(await (await download).path())),hash(readFileSync(path)));
        const action=page.locator('.contract-action-form');await action.locator('[name=action]').selectOption('accept_contract');await action.locator('[name=reviewer]').fill('Browser test reviewer');await action.locator('[name=rationale]').fill('Original and exact comparison inspected for this synthetic test.');
        assert.equal(await action.evaluate(form=>form.checkValidity()),false);
        await action.locator('[name=independent_original_reviewed]').check();
        const accepted=page.waitForResponse(r=>r.url().endsWith('/api/contract-actions'));
        await action.getByRole('button',{name:'Record contract action'}).click();assert.equal((await accepted).status(),201);
        await page.getByText('Contract action · accept contract',{exact:true}).waitFor();
        await page.getByRole('heading',{name:'Review history',exact:true}).scrollIntoViewIfNeeded();await shot(page,'desktop-exact-acceptance');
      }
    }
    checks.push('exact NDA and exact order auto-compare with zero differences and pending human action; exact NDA accepts only after original-review acknowledgement');
    assert.deepEqual(errors,[]);assert(writes.every(w=>w.status===201));assert.equal(writes.filter(w=>w.url==='/api/finding-assessments').length,2);assert.equal(writes.filter(w=>w.url==='/api/contract-actions').length,2);
    writeFileSync(join(evidence,'browser-results.json'),JSON.stringify({browser:await browser.version(),base,viewports:['1440x1000','390x844'],checks,errors,writes,screenshots},null,2));
    console.log(JSON.stringify({checks,errors,evidence},null,2));
  }catch(error){if(page){await page.screenshot({path:join(evidence,'failure.png'),fullPage:false});writeFileSync(join(evidence,'failure.txt'),await page.locator('body').innerText());console.error(await page.evaluate(()=>[...document.querySelectorAll('*')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width,text:e.textContent.slice(0,90)})).slice(0,20)));}throw error}finally{if(browser)await browser.close();await stop()}
})().catch(e=>{console.error(e);process.exitCode=1});
