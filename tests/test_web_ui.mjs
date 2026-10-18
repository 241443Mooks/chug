import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
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
    document:{getElementById:node,querySelectorAll:()=>[],addEventListener:()=>{},title:''},
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
  await assert.rejects(h.run("api('/api/queue')"),/Invalid or empty JSON response/);
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

test('reference page lists family, approval status and a detail action for the local library',()=>{
  const h=harness(items,'127.0.0.1');
  h.run("state.reference={current:{filename:'baseline.docx',kind:'bundled',sha256:'abc',coverage:{status:'complete'},source_integrity:'verified',units:[]},available:[]}");
  h.run("state.referenceLibrary={references:[{reference_id:'UP-123',display_name:'Fictional order',family:'customer_order',status:'registered_for_evaluation',approval_status:'unapproved',version:'1.0',source_integrity:'verified',sha256:'123'}],count:1}");
  h.run("state.referenceDetail={reference_id:'UP-123',display_name:'Fictional order',family:'customer_order',status:'registered_for_evaluation',approval_status:'unapproved',version:'1.0',provenance:'local upload',original_filename:'order.docx',sha256:'123',source_integrity:'verified',variant:null,deployment:null,channel:null,jurisdiction:null,extraction:{status:'complete',passage_count:4,limitations:[]},original_url:'/api/reference-library/UP-123/original'}");
  const page=h.run('referenceView()');
  assert.match(page,/Reference standards/);
  assert.match(page,/customer order · registered for evaluation/);
  assert.match(page,/data-reference-detail="UP-123"/);
  assert.match(page,/Fictional order · unapproved/);
  assert.match(page,/Download exact original DOCX/);
});

test('public reference page keeps its standard upload control hidden',()=>{
  const h=harness(items,'chug.smooks.co.uk');
  const uploadControl={hidden:false};
  h.context.document.querySelectorAll=selector=>selector.startsWith('.upload-button')?[uploadControl]:[];
  h.run('applyStaticDemo()');
  assert.equal(uploadControl.hidden,true);
});
