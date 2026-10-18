import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';

const source=readFileSync(new URL('../web/app.js',import.meta.url),'utf8').split("loadQueue().then(async()=>")[0];
const html=readFileSync(new URL('../web/index.html',import.meta.url),'utf8');
const css=readFileSync(new URL('../web/styles.css',import.meta.url),'utf8');
const falcon=JSON.parse(readFileSync(new URL('../web/demo-data/contracts/T03.json',import.meta.url),'utf8'));

function harness(items,hostname='localhost'){
  const elements=new Map();
  const clicks=[];
  const node=id=>{
    if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',value:'',className:'',querySelectorAll:()=>[],querySelector:()=>null,click:()=>clicks.push(id)});
    return elements.get(id);
  };
  const location={hash:'#home',hostname};
  const storage=new Map();
  const context=vm.createContext({
    document:{getElementById:node,querySelectorAll:()=>[],addEventListener:()=>{},body:{classList:{add:()=>{}}},title:''},
    location,
    sessionStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},
    window:{history:{pushState:(_state,_title,hash)=>{location.hash=hash},replaceState:(_state,_title,hash)=>{location.hash=hash}},addEventListener:()=>{}},
    fetch:async url=>({ok:true,json:async()=>url==='/api/queue'?{items}:null}),
    requestAnimationFrame:()=>{},
    setTimeout,clearTimeout,
  });
  vm.runInContext(source,context);
  return {context,node,location,storage,clicks,run:code=>vm.runInContext(code,context)};
}

const items=[
  {id:'T03',display_name:'Falcon',route:'escalate',findings_count:3,reason:'Broad rights',latest_decision:null},
  {id:'T04',display_name:'Elm',route:'escalate',findings_count:1,reason:'Missing protection',latest_decision:{decision:'escalate'}},
  {id:'T02',display_name:'Brookside',route:'review_required',findings_count:1,reason:'Changed term',latest_decision:null},
  {id:'T01',display_name:'Birchbridge',route:'routine_candidate',findings_count:0,reason:'No material change',latest_decision:null},
];

test('Home counts pending work and each category opens its filtered queue',async()=>{
  const h=harness(items);
  h.run('state.queue = '+JSON.stringify(items));
  const home=h.run('homeView()');
  assert.match(home,/data-filter="escalate"><strong>1<\/strong>/);
  assert.match(home,/data-filter="review_required"><strong>1<\/strong>/);
  assert.match(home,/data-filter="routine_candidate"><strong>1<\/strong>/);
  assert.match(home,/Start reviewing/);
  await h.run("navigate('queue','escalate')");
  assert.equal(h.location.hash,'#queue/escalate');
  assert.equal(h.node('filter').value,'escalate');
  assert.match(h.node('queue').innerHTML,/Falcon/);
  assert.doesNotMatch(h.node('queue').innerHTML,/Elm|Brookside/);
  assert.equal(h.storage.get('chug.queueFilter'),'escalate');
  await h.run("navigate('queue','review_required')");
  assert.match(h.node('queue').innerHTML,/Brookside/);
  assert.doesNotMatch(h.node('queue').innerHTML,/Falcon/);
  await h.run("navigate('queue','routine_candidate')");
  assert.match(h.node('queue').innerHTML,/Birchbridge/);
});

test('decision controls retain human outcomes, rationale and finding selection',()=>{
  const h=harness(items);
  const html=h.run("decisionView({analysis:{findings:[{id:'finding-1',title:'Broad rights'}]}})");
  for(const outcome of ['approve','request_amendment','reject','escalate'])assert.match(html,new RegExp(`value="${outcome}"`));
  assert.match(html,/name="reviewer" required/);
  assert.match(html,/name="rationale" required/);
  assert.match(html,/name="finding" value="finding-1"/);
  assert.match(html,/Recording a decision does not publish it as precedent/);
});

test('Falcon overview follows the four reviewer questions and puts decision entry before secondary detail',()=>{
  const h=harness(items);
  h.run('state.detail = '+JSON.stringify(falcon));
  const html=h.run('overview(state.detail)');
  const order=['1. What changed?','2. Why might it matter?','3. What does the original wording and reference say?','4. What should you do next?'];
  let previous=-1;
  for(const label of order){const at=html.indexOf(label);assert.ok(at>previous,`${label} should follow the previous review question`);previous=at;}
  assert.match(html,/Potentially broad use or IP rights/);
  assert.match(html,/commercially exploit all technical concepts/);
  assert.match(html,/No intellectual property licence or other right is granted/);
  assert.match(html,/data-open-decision aria-controls="decision-section"/);
  assert.ok(html.indexOf('data-open-decision')<html.indexOf('Other findings'));
  assert.match(html,/<details class="decision-disclosure" id="decision-section">/);
  assert.match(html,/<details class="other-findings">/);
  assert.match(html,/<details class="finding-tools">/);
  assert.match(html,/Pattern-based flag; a reviewer must interpret the complete provision/);
  assert.match(css,/\.next-step\{[^}]*justify-content:space-between/);
  assert.match(css,/@media\(max-width:700px\)[\s\S]*?\.decision-action\{width:100%\}/);
});

test('Add DOCX is a keyboard-operable native button wired to the existing picker',()=>{
  const h=harness(items);
  assert.match(html,/<button class="upload-button" id="upload-trigger" type="button">Add DOCX<\/button>/);
  assert.match(html,/<input id="upload" type="file" accept="\.docx" hidden>/);
  assert.equal(typeof h.node('upload-trigger').onclick,'function');
  h.node('upload-trigger').onclick();
  assert.deepEqual(h.clicks,['upload']);
});

test('queue title and route badge can wrap without collapsing the title column',()=>{
  assert.match(css,/\.queue-item-top\{[^}]*flex-wrap:\s*wrap/);
  assert.match(css,/\.queue-item-title\{[^}]*min-width:\s*11ch[^}]*flex:\s*1\s+1\s+11ch/);
});

test('Start reviewing carries the next contract category back to the queue',async()=>{
  const h=harness(items);
  h.run('state.queue = '+JSON.stringify(items));
  h.run("state.page='home'; select=async id=>{globalThis.selectedId=id}");
  await h.run('startReviewing()');
  assert.equal(h.context.selectedId,'T03');
  assert.equal(h.run('state.filter'),'escalate');
  assert.equal(h.storage.get('chug.queueFilter'),'escalate');
});

test('static hosting falls back to synthetic snapshot and refuses writes',async()=>{
  const h=harness(items);
  const calls=[];
  h.context.fetch=async(url,options)=>{
    calls.push(url);
    if(url==='/api/queue')return {ok:true,headers:{get:()=> 'text/html'},json:async()=>{throw new Error('HTML is not data')}};
    if(url==='/demo-data/queue.json')return {ok:true,headers:{get:()=> 'application/json'},json:async()=>({items})};
    if(url==='/demo-data/contracts/T01.json')return {ok:true,headers:{get:()=> 'application/json'},json:async()=>({id:'T01'})};
    throw new Error('Unexpected fetch: '+url);
  };
  const snapshot=await h.run("api('/api/queue')");
  assert.equal(snapshot.items.length,4);
  assert.equal(h.run('state.staticDemo'),true);
  assert.equal((await h.run("api('/api/contracts/T01')")).id,'T01');
  await assert.rejects(h.run("api('/api/decisions',{method:'POST'})"),/Read-only public demo/);
  assert.deepEqual(calls,['/api/queue','/demo-data/queue.json','/demo-data/contracts/T01.json']);
});

test('public demo handles empty JSON responses from a static Worker without a Python API',async()=>{
  const h=harness(items);
  const calls=[];
  h.context.fetch=async url=>{
    calls.push(url);
    if(url==='/api/queue')return {ok:true,status:200,headers:{get:()=>null},json:async()=>{throw new SyntaxError('Unexpected end of JSON input')}};
    if(url==='/demo-data/queue.json')return {ok:true,status:200,headers:{get:()=> 'application/json'},json:async()=>({items})};
    throw new Error('Unexpected fetch: '+url);
  };
  const snapshot=await h.run("api('/api/queue')");
  assert.equal(snapshot.items.length,4);
  assert.equal(h.run('state.staticDemo'),true);
  assert.deepEqual(calls,['/api/queue','/demo-data/queue.json']);
});

test('real API errors are not silently hidden behind the public snapshot',async()=>{
  const h=harness(items);
  h.context.fetch=async url=>{
    if(url==='/api/queue')return {ok:false,status:500,headers:{get:()=> 'application/json'},json:async()=>{throw new SyntaxError('Unexpected end of JSON input')}};
    throw new Error('Unexpected public snapshot fallback: '+url);
  };
  await assert.rejects(h.run("api('/api/queue')"),/Chug could not read the data for this page/);
  assert.equal(h.run('state.staticDemo'),false);
});

test('public Cloudflare hostname reads the static queue directly and blocks write actions',async()=>{
  const h=harness(items,'chug.smooks.co.uk');
  const calls=[];
  h.context.fetch=async(url)=>{
    calls.push(url);
    const fixtures={
      '/demo-data/queue.json':{items},
      '/demo-data/reference.json':{current:{kind:'bundled'}},
      '/demo-data/contracts/T03.json':{id:'T03'},
      '/demo-data/history/H03.json':{document:{id:'H03'}},
    };
    if(!(url in fixtures))throw new Error('Unexpected API request: '+url);
    return {ok:true,headers:{get:()=> 'application/json'},json:async()=>fixtures[url]};
  };
  assert.equal(h.run('state.staticDemo'),true);
  assert.equal((await h.run("api('/api/queue')")).items.length,4);
  assert.equal((await h.run("api('/api/reference')")).current.kind,'bundled');
  assert.equal((await h.run("api('/api/contracts/T03')")).id,'T03');
  assert.equal((await h.run("api('/api/history/H03')")).document.id,'H03');
  await assert.rejects(h.run("api('/api/decisions',{method:'POST'})"),/Read-only public demo/);
  assert.deepEqual(calls,[
    '/demo-data/queue.json',
    '/demo-data/reference.json',
    '/demo-data/contracts/T03.json',
    '/demo-data/history/H03.json',
  ]);
});

test('slash-prefixed public review deep links resolve the selected review and tab',()=>{
  const h=harness(items,'chug.smooks.co.uk');
  h.location.hash='#/review/T03/overview';
  assert.deepEqual({...h.run('route()')},{page:'review',id:'T03',tab:'overview',anchor:null});
  h.location.hash='#/review/T05/comparison';
  assert.deepEqual({...h.run('route()')},{page:'review',id:'T05',tab:'comparison',anchor:null});
});

test('public queue renders every precomputed review as an open-review button',()=>{
  const h=harness(items,'chug.smooks.co.uk');
  h.run('state.staticDemo=true;state.queue='+JSON.stringify(items));
  const html=h.run('queueView()');
  assert.equal((html.match(/class="public-review-card"/g)||[]).length,items.length);
  for(const item of items)assert.match(html,new RegExp(`data-id="${item.id}"`));
  assert.match(html,/A person must make each decision/);
  assert.equal((html.match(/<option value="all"/g)||[]).length,1);
  assert.match(html,/public-filter/);
});

test('public filter state is transient and is not written to session storage',async()=>{
  const h=harness(items,'chug.smooks.co.uk');
  h.run('state.queue='+JSON.stringify(items));
  await h.run("navigate('queue','escalate')");
  assert.equal(h.storage.has('chug.queueFilter'),false);
  assert.equal(h.run('state.filter'),'escalate');
});

test('public Start reviewing does not persist the chosen category',async()=>{
  const h=harness(items,'chug.smooks.co.uk');
  h.run('state.queue='+JSON.stringify(items)+';state.staticDemo=true;state.page="home";select=async id=>id');
  assert.equal(await h.run('startReviewing()'),'T03');
  assert.equal(h.storage.has('chug.queueFilter'),false);
});

test('full comparison exposes all exported wording and links finding passages',()=>{
  const h=harness(items,'chug.smooks.co.uk');
  h.run('state.detail='+JSON.stringify(falcon));
  const html=h.run('comparisonView(state.detail)');
  assert.match(html,/Full wording comparison/);
  assert.match(html,/Applicable reference/);
  assert.match(html,/data-finding-index=/);
  assert.match(html,new RegExp(`${falcon.document.units.length} incoming passages`));
  assert.match(html,new RegExp(`${falcon.reference.units.length} reference passages`));
  for(const unit of falcon.document.units)assert.ok(html.includes(unit.text),`incoming wording missing: ${unit.anchor}`);
  for(const unit of falcon.reference.units)assert.ok(html.includes(unit.text),`reference wording missing: ${unit.anchor}`);
});

test('every exported incoming review has inspectable incoming and reference wording',()=>{
  const ids=readdirSync(new URL('../web/demo-data/contracts/',import.meta.url)).filter(name=>/^T\d+\.json$/.test(name));
  assert.equal(ids.length,6);
  for(const name of ids){
    const detail=JSON.parse(readFileSync(new URL('../web/demo-data/contracts/'+name,import.meta.url),'utf8'));
    const h=harness(items,'chug.smooks.co.uk');
    h.run('state.detail='+JSON.stringify(detail));
    const html=h.run('comparisonView(state.detail)');
    assert.match(html,/Incoming contract/);
    assert.match(html,/Applicable reference/);
    for(const unit of detail.document.units)assert.ok(html.includes(unit.text),`${name} omitted ${unit.anchor}`);
    for(const unit of detail.reference.units)assert.ok(html.includes(unit.text),`${name} omitted reference ${unit.anchor}`);
  }
});

test('local Python host keeps the interactive API enabled',async()=>{
  const h=harness(items,'127.0.0.1');
  const calls=[];
  h.context.fetch=async(url)=>{
    calls.push(url);
    if(url==='/api/queue')return {ok:true,headers:{get:()=> 'application/json'},json:async()=>({items})};
    if(url==='/api/decisions')return {ok:true,headers:{get:()=> 'application/json'},json:async()=>({id:'new-decision'})};
    throw new Error('Unexpected request: '+url);
  };
  assert.equal(h.run('state.staticDemo'),false);
  assert.equal((await h.run("api('/api/queue')")).items.length,4);
  assert.equal((await h.run("api('/api/decisions',{method:'POST'})")).id,'new-decision');
  assert.deepEqual(calls,['/api/queue','/api/decisions']);
});

test('reference page lists family and lifecycle status with detail, matching and original actions',()=>{
  const h=harness(items,'127.0.0.1');
  h.run("state.reference={current:{filename:'baseline.docx',kind:'bundled',sha256:'abc',coverage:{status:'complete'},source_integrity:'verified',units:[]},available:[]}");
  h.run("state.referenceLibrary={references:[{reference_id:'UP-123',display_name:'Fictional order',family:'customer_order',status:'active',version:'1.0',source_integrity:'verified',sha256:'123'}],count:1}");
  h.run("state.referenceDetail={reference_id:'UP-123',display_name:'Fictional order',family:'customer_order',status:'active',kind:'uploaded_synthetic',version:'1.0',provenance:'local upload',original_filename:'order.docx',sha256:'123',source_integrity:'verified',variant:null,deployment:null,channel:null,jurisdiction:null,extraction:{status:'complete',passage_count:4,limitations:[]},original_url:'/api/reference-library/UP-123/original'}");
  const page=h.run('referenceView()');
  assert.match(page,/Reference documents/);
  assert.match(page,/customer order · active/);
  assert.match(page,/data-reference-detail="UP-123"/);
  assert.match(page,/Fictional order · active/);
  assert.match(page,/Download exact original DOCX/);
  assert.match(page,/Mark Superseded/);
  assert.match(page,/Mark Withdrawn/);
  assert.match(page,/Check reference applicability/);
});

test('local reference library groups fictional standards, the legacy NDA baseline and research provenance',()=>{
  const h=harness(items,'127.0.0.1');
  h.run("state.reference={current:{filename:'bundled.docx',kind:'bundled',sha256:'base',coverage:{status:'complete'},source_integrity:'verified',units:[]},available:[]}");
  h.run("state.referenceLibrary={references:[{reference_id:'BASE-base',display_name:'Bundled mutual NDA',family:'nda',status:'legacy_nda_baseline',version:'bundled',provenance:'bundled_demo_baseline',source_integrity:'verified',sha256:'base'},{reference_id:'UP-order',display_name:'Fictional order',family:'customer_order',status:'active',version:'1.0',provenance:'locally_uploaded_synthetic_reference',source_integrity:'verified',sha256:'order'},{reference_id:'NDA-1',display_name:'Research NDA',family:'nda',status:'research_candidate',version:'0.1',provenance:'verified_research_catalogue',source_integrity:'verified',sha256:'research'}]}");
  const page=h.run('referenceView()');
  assert.match(page,/This library shows the type, version and status/);
  assert.match(page,/References added by Legal/);
  assert.match(page,/Fictional Legal upload/);
  assert.match(page,/Original NDA reference/);
  assert.match(page,/will not suggest it for new contracts/);
  assert.match(page,/Examples for testing — not reference documents/);
  assert.doesNotMatch(page,/Research library · not active review standards|not been approved as organisational guidance/);
  assert.match(h.run('helpView()'),/What is a reference/);
  assert.match(h.run('helpView()'),/public demo only shows fictional examples/);
});

test('public reference view is read-only and keeps standards separate from incoming examples',()=>{
  const h=harness(items,'chug.smooks.co.uk');
  h.run("state.research={references:Array.from({length:8},(_,i)=>({id:'R'+i,name:'Research standard '+i,family:'nda',version:'0.1',sha256:'hash'+i,download:'/research/'+i+'.docx'})),routine_clients:[{name:'Client example',family:'incoming',download:'/client.docx'}],challenge_cases:[{name:'Challenge example',family:'incoming',download:'/challenge.docx'}]}");
  const page=h.run('referenceView()');
  assert.match(page,/You can view the files, but you cannot upload or compare new contracts here/);
  assert.match(page,/Examples for testing — not reference documents/);
  assert.match(page,/8 fictional examples/);
  assert.match(page,/Example contracts — not references/);
  assert.match(page,/client contract examples \(not checked\)/);
  assert.match(page,/examples with possible problems \(not checked\)/);
  assert.doesNotMatch(page,/id="reference-upload"|id="match-upload"|data-use-reference|data-select-reference/);
  assert.doesNotMatch(page,/future work \(#21\)|live multi-family comparison is available/);
});

test('matching result exposes context, source identity, excluded candidates and human boundary',()=>{
  const h=harness(items);
  h.run('state.matchResult='+JSON.stringify({incoming:{filename:'incoming.docx',sha256:'abc'},assessed_at:'2026-10-18',original_url:'/incoming.docx',proposal:{status:'proposed',reason:'One context-compatible reference remains.',human_confirmation_required:true,comparison_allowed:false,proposal:{reference_id:'UP-123',display_name:'Fictional order',status:'active',version:'1.0',sha256:'123',reasons:[{dimension:'variant',value:'desktop_seats',evidence:[{anchor:'word/document.xml:p2',text:'Direct desktop order'}]}]},context:{dimensions:{channel:{state:'known',value:'direct',evidence:[]}}},excluded:[{display_name:'Old order',status:'withdrawn',reasons:['inactive standards are excluded from new matches']}]}}));
  const result=h.run('matchResultView(state.matchResult)');
  assert.match(result,/Fictional order/);
  assert.match(result,/word\/document.xml:p2/);
  assert.match(result,/withdrawn/);
  assert.match(result,/Human decision required/);
  assert.match(result,/Confirmation and comparison have not occurred/);
});

test('new intake detail shows a provisional comparison with source anchors and truthful pending states',()=>{
  const h=harness(items);
  h.run('state.intake='+JSON.stringify({
    document:{filename:'New fictional NDA.docx',units:[{anchor:'word/document.xml:p4',text:'Confidentiality lasts seven years.'}]},
    incoming:{sha256:'abc'},family:'nda',status:'analysed_needs_review',route:'review_required',reason:'Provisional comparison is complete; a person must decide.',
    extraction:{status:'complete'},original_url:'/api/intakes/abc/original',
    matching:{proposal:{status:'proposed',reason:'One context-compatible reference remains.',proposal:{reference_id:'UP-123',display_name:'Fictional NDA',version:'1.0',sha256:'ref',reasons:[{dimension:'variant',value:'mutual_evaluation',evidence:[{anchor:'word/document.xml:p2',text:'Purpose: product evaluation.'}]}]}}},
    comparison:{status:'analysed',findings:[{title:'Changed retention',explanation:'The period differs.',sources:[{anchor:'word/document.xml:p4',text:'Confidentiality lasts seven years.'}],reference:{anchor:'word/document.xml:p4',text:'Confidentiality lasts five years.'}}]},
    analysis:{findings:[{title:'Changed retention',explanation:'The period differs.',sources:[{anchor:'word/document.xml:p4',text:'Confidentiality lasts seven years.'}],reference:{anchor:'word/document.xml:p4',text:'Confidentiality lasts five years.'}}]}
  }));
  const complete=h.run('intakeView(state.intake)');
  assert.match(complete,/Proposed reference · not confirmed/);
  assert.match(complete,/word\/document.xml:p4/);
  assert.match(complete,/provisional NDA comparison/);
  assert.match(complete,/Download exact incoming DOCX/);
  assert.match(complete,/Record your review decision/);
  assert.match(complete,/Confirm reference and compare/);
  assert.match(complete,/independently inspect the exact incoming original/);
  assert.match(complete,/independent_original_reviewed/);
  assert.match(source,/reviewed\.required=decision\.value==='approve'/);
  h.run('state.intake='+JSON.stringify({document:{filename:'Unmatched.docx',units:[]},incoming:{sha256:'pending'},family:'customer_order',status:'awaiting_reference',route:'review_required',reason:'A reviewer must confirm the reference.',extraction:{status:'complete'},matching:{proposal:{reason:'No suitable match.'}},comparison:{status:'not_run',reason:'Explicit confirmation is required.'},original_url:'/api/intakes/pending/original'}));
  const pending=h.run('intakeView(state.intake)');
  assert.match(pending,/Analysis incomplete · no quick-review result/);
  assert.match(pending,/Extraction: complete\. Comparison: not_run/);
  assert.match(pending,/Comparison not run/);
  assert.match(pending,/independently inspect the exact incoming original/);
  assert.match(pending,/Explicit confirmation is required/);
  assert.match(pending,/Record your review decision/);
  assert.doesNotMatch(pending,/Looks routine|Approved/);
  h.run('state.intake='+JSON.stringify({document:{filename:'Corrupted.docx',units:[]},incoming:{sha256:'blocked'},family:null,status:'blocked_extraction',route:'blocked_extraction',reason:'The DOCX could not be read.',extraction:{status:'blocked'},matching:{proposal:{reason:'Extraction is incomplete.'}},comparison:{status:'not_run',reason:'Extraction is incomplete; comparison was not performed.'},original_url:'/api/intakes/blocked/original'}));
  const blocked=h.run('intakeView(state.intake)');
  assert.match(blocked,/Analysis incomplete · no quick-review result/);
  assert.match(blocked,/Extraction: blocked\. Comparison: not_run/);
  assert.match(blocked,/role="alert"/);
  assert.ok(blocked.indexOf('Analysis incomplete')<blocked.indexOf('Record your review decision'));
  h.run('state.intake='+JSON.stringify({document:{filename:'Prior review.docx',units:[]},incoming:{sha256:'old'},family:'nda',status:'analysed_needs_review',route:'review_required',reason:'Saved comparison.',extraction:{status:'complete'},source_integrity:{incoming:'verified',reference:'unavailable'},matching:{proposal:{reason:'Previously selected.'}},comparison:{status:'analysed',findings:[]},original_url:'/api/intakes/old/original'}));
  assert.match(h.run('intakeView(state.intake)'),/Reference source unavailable/);
  h.run('state.intake.source_integrity.reference="not_linked"');
  assert.doesNotMatch(h.run('intakeView(state.intake)'),/Reference source not_linked/);
});

test('public reference page keeps its standard upload control hidden',()=>{
  const h=harness(items,'chug.smooks.co.uk');
  const uploadControl={hidden:false};
  h.context.document.querySelectorAll=selector=>selector.startsWith('.upload-button')?[uploadControl]:[];
  h.run('applyStaticDemo()');
  assert.equal(uploadControl.hidden,true);
});

test('selected reference view preserves source identity and avoids an approval claim',()=>{
  const h=harness(items,'chug.smooks.co.uk');
  h.run('state.detail='+JSON.stringify(falcon));
  const html=h.run('referenceTextView(state.detail)');
  assert.match(html,/Reference used for this review/);
  assert.match(html,/bundled synthetic mutual NDA baseline bound to this precomputed review/);
  assert.match(html,new RegExp(falcon.reference.sha256));
  assert.match(html,/do not establish current organisational approval/);
});


test('public pages use clear tasks and keep human decision limits visible',()=>{
  const h=harness(items,'chug.smooks.co.uk');
  const home=h.run('homeView()');
  const queue=h.run('queueView()');
  const help=h.run('helpView()');
  assert.match(home,/Review a contract/);
  assert.match(home,/You decide what happens next/);
  assert.match(queue,/These labels help you choose what to check/);
  assert.match(help,/Open the review queue/);
  assert.match(help,/You cannot save a decision on this public site/);
  assert.match(help,/A past decision does not approve a new contract/);
  assert.match(help,/AI cannot approve a contract/);
  const history=readFileSync(new URL('../web/decision-log.html',import.meta.url),'utf8');
  assert.match(history,/These decisions are made up/);
  assert.match(history,/Do not use these examples as approval/);
});
