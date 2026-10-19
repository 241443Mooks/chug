/** Verify the fresh public static export locally; requires Playwright and Chromium.
 * CHUG_CHROMIUM_EXECUTABLE=/path/to/chrome node scripts/browser_public_review.cjs /tmp/evidence
 */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const {mkdirSync,writeFileSync}=require('node:fs');
const {resolve,join}=require('node:path');
const assert=require('node:assert/strict');
const net=require('node:net');
const root=resolve(__dirname,'..'),evidence=resolve(process.argv[2]||'/tmp/chug-public-browser');
mkdirSync(evidence,{recursive:true});
(async()=>{
  const port=await new Promise(r=>{const s=net.createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>r(p))})});
  const server=spawn('python3',['-u','-m','http.server',String(port),'--bind','127.0.0.1','--directory',join(root,'web')]);
  let browser;const errors=[],posts=[];
  try{
    await new Promise((r,j)=>{server.stdout.once('data',r);server.once('error',j)});
    browser=await chromium.launch({headless:true,executablePath:process.env.CHUG_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']});
    const context=await browser.newContext({viewport:{width:1440,height:1000}});
    // Exercise a public hostname using the actual local static files. There is no API backend.
    await context.route('http://public-chug.test/**',async route=>{
      if(route.request().method()!=='GET')posts.push(route.request().url());
      const url=new URL(route.request().url());
      const response=await context.request.get(`http://127.0.0.1:${port}${url.pathname}`);
      await route.fulfill({response});
    });
    const page=await context.newPage();page.setDefaultTimeout(10000);
    page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(['warning','error'].includes(m.type()))errors.push(m.text())});
    await page.goto('http://public-chug.test/#/review/T05/overview');
    await page.locator('.finding-summary').first().waitFor();assert.equal(await page.locator('.finding-summary').count(),4);
    await page.locator('.finding-summary').nth(1).click();await page.getByRole('heading',{name:'Example finding assessments',exact:true}).waitFor();
    assert.equal(await page.locator('form:visible').count(),0);
    assert.match(await page.locator('#workspace').innerText(),/Deal breaker/);
    await page.screenshot({path:join(evidence,'public-finding.png')});
    await page.getByRole('button',{name:'← Back to findings',exact:true}).click();
    await page.locator('#decision-section > summary').click();await page.getByRole('heading',{name:'Example contract outcomes',exact:true}).waitFor();
    assert.match(await page.locator('#workspace').innerText(),/Accept contract/);
    await page.getByRole('button',{name:'Compare documents',exact:true}).click();
    await page.locator('.full-comparison').waitFor();assert((await page.locator('#workspace').innerText()).length>500);
    await page.reload();await page.locator('#workspace').getByText('Incoming contract',{exact:true}).first().waitFor();
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
    await page.screenshot({path:join(evidence,'public-mobile.png')});
    assert.equal(await page.locator('#incoming-upload').isVisible(),false);
    assert.equal(await page.locator('form:visible').count(),0);assert.deepEqual(posts,[]);assert.deepEqual(errors,[]);
    writeFileSync(join(evidence,'public-results.json'),JSON.stringify({browser:await browser.version(),environment:'local static export at simulated public hostname; not deployed website',viewports:['1440x1000','390x844'],checks:['T05 direct link -> second finding -> example assessments -> back -> example contract outcomes -> full comparison -> refresh','no visible forms or upload controls; zero POST requests','no horizontal overflow at 390px'],errors,posts},null,2));
    console.log('Public static browser checks passed; evidence: '+evidence);
  }finally{if(browser)await browser.close();server.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
