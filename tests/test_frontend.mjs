// Lightweight DOM harness for the actual page script. This is not a graphical browser test.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
class Element {
 constructor(tag='div'){this.tag=tag;this.children=[];this.textContent='';this.dataset={};this.disabled=false;this.className='';}
 append(e){this.children.push(e)}
 replaceChildren(){this.children=[];this.textContent=''}
 addEventListener(type,fn){this.listeners??={};this.listeners[type]=fn}
}
const html=fs.readFileSync(new URL('../web/index.html',import.meta.url),'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const ids=Object.fromEntries(['coverage','sources','decisions','requests','detail','error'].map(id=>[id,new Element()]));
const buttons=['correct','review','metadata','missing_links','reset'].map(op=>{const b=new Element('button');b.dataset.op=op;return b});
const runs=JSON.parse(fs.readFileSync(new URL('../results/captured_runs.json',import.meta.url),'utf8'));
const initial=runs.find(c=>c.case_id==='relevant_time').before;
let state=initial;
const context=vm.createContext({document:{getElementById:id=>ids[id],createElement:tag=>new Element(tag),querySelectorAll:()=>buttons},Intl,Date,Map,Set,JSON,Error,fetch:async()=>({ok:true,json:async()=>state})});
new vm.Script(script).runInContext(context);
await new Promise(r=>setImmediate(r));
const flatten=e=>[e.textContent,...e.children.map(flatten)].join(' ');
assert.match(flatten(ids.coverage),/complete within the declared records/);
state=runs.find(c=>c.case_id==='relevant_time').after;
await vm.runInContext('action("correct")',context);
assert.equal(ids.requests.children.length,1);
assert.match(flatten(ids.requests),/14:40.*15:40/);
assert.match(flatten(ids.requests),/No identity, lead validity, or recovery conclusion/);
state=runs.find(c=>c.case_id==='review_successor').after;
await vm.runInContext('action("review")',context);
assert.match(flatten(ids.decisions),/Retained; superseded/);
state=runs.find(c=>c.case_id==='missing_edges').after;
await vm.runInContext('action("missing_links")',context);
assert.match(flatten(ids.coverage),/incomplete/);
assert.match(flatten(ids.requests),/No targeted request/);
// The actual renderer assigns source strings through textContent, not HTML.
state=structuredClone(initial);state.nodes.find(n=>n.kind==='decision').rationale='<img src=x onerror=attack()>'.repeat(2);
context.testState=state;vm.runInContext('render(testState)',context);
assert.match(flatten(ids.decisions),/<img/);
assert.equal(ids.decisions.children[0].children[2].children.length,0);
console.log('PASS: page-script rendering, correction, review history, missing-link warning, literal source text. Graphical browser unavailable.');
