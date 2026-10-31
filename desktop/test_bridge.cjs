const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/../index.html','utf8');const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const ids=[...html.matchAll(/id="([^"]+)"/g)].map(x=>x[1]);assert.equal(new Set(ids).size,ids.length);
for(const [,id] of js.matchAll(/\$\('([^']+)'\)/g))assert(ids.includes(id),id);
function fakeNode(){const classes=new Set(),listeners={};return {children:[],attrs:{},classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),contains:x=>classes.has(x),toggle(x,force){if(force===true)classes.add(x);else if(force===false)classes.delete(x);else if(classes.has(x))classes.delete(x);else classes.add(x)}},style:{},value:'',paused:true,currentTime:0,readyState:4,seeking:false,playbackRate:1,addEventListener(name,fn){(listeners[name]??=[]).push(fn)},removeEventListener(name,fn){listeners[name]=(listeners[name]||[]).filter(f=>f!==fn)},emit(name){for(const fn of listeners[name]||[])fn()},setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]},load(){},focus(){this.focused=true},append(...items){this.children.push(...items)},click(){this.onclick?.()},remove(){},querySelector(name){return this.parts??=Object.create(null),this.parts[name]??=fakeNode()},pause(){this.paused=true;this.onpause?.()},async play(){this.paused=false;this.onplay?.()},getContext(){return {drawImage(){},getImageData(){return {data:new Uint8Array(576*4)}}}},_text:'',get textContent(){return this._text},set textContent(v){this._text=v;this.children=[]},get innerHTML(){return this._html||''},set innerHTML(v){this._html=v;this.children=[]}}}
const elements={};for(const id of ids){const node=fakeNode();const markup=html.match(new RegExp('<[^>]*id="'+id+'"[^>]*>'))?.[0]||'';for(const c of markup.match(/class="([^"]*)"/)?.[1].split(' ')||[])node.classList.add(c);node.value={brightness:'50',speed:'1',patternFilter:'all',playbackMode:'preview',exportFormat:'text'}[id]||'';elements[id]=node}
const body=fakeNode(),created=[];const context=vm.createContext({document:{body,createTextNode:text=>({textContent:text}),getElementById:id=>elements[id],querySelectorAll:selector=>{const all=[];function walk(n){for(const child of n.children||[]){if(child.className===selector.slice(1))all.push(child);walk(child)}}walk(elements.segments);return all},createElement:tag=>{const n=fakeNode();n.tag=tag;created.push(n);return n}},console,Float32Array,Uint8Array,Blob,URL:{revokeObjectURL(){},createObjectURL:()=> 'blob:report'},setTimeout,clearTimeout,setInterval,clearInterval,requestAnimationFrame:()=>1,cancelAnimationFrame(){}});vm.runInContext(js,context);
const evaluate=s=>vm.runInContext(s,context);

let state={status:'idle'};
context.window={FLASHGUARD_WINDOW_MARKER:'FG-test',addEventListener(){}};
context.navigator={sendBeacon(){}};
context.document.addEventListener=()=>{};
context.fetch=async route=>({ok:true,json:async()=>route==='api/status'?state:{connected:true}});
context.setTimeout=()=>0;context.setInterval=()=>0;context.clearInterval=()=>{};
vm.runInContext(fs.readFileSync(__dirname+'/bridge.js','utf8'),context);
(async()=>{
await new Promise(resolve=>setImmediate(resolve));
state={status:'analyzing',videoName:'restored.mp4',frames:1200,progress:30,message:'Restoring decoder to the saved position…'};
await evaluate('restoreDesktopSession()');await new Promise(resolve=>setImmediate(resolve));
assert.equal(elements.player.src,'video');assert.equal(elements.player.paused,true);
assert.equal(elements.details.textContent,'restored.mp4');
assert.match(elements.status.textContent,/Restoring decoder/);
assert.equal(elements.progress.attrs['aria-valuenow'],30);
state={status:'complete',videoName:'restored.mp4',result:{complete:true,video:{name:'restored.mp4',durationSeconds:400},settings:{analyzedSamples:4000,elapsedSeconds:4,resumedSamples:1200},segments:[{start:1,end:2,kind:'Rapid light changes',patterns:['brightness'],cue:'Dark frame'}]}};
await evaluate('pollDesktop()');
assert.equal(evaluate('reportData.complete'),true);assert.equal(evaluate('segments.length'),1);
assert(!elements.resultsView.classList.contains('hidden'));assert.equal(elements.saveReport.disabled,false);
assert.equal(evaluate('exportReport().settings.resumedSamples'),1200);
console.log('PASS: restored active session reconnects without choosing/uploading a video; decoder catch-up status, saved progress, completed report, and export restored.');
})().catch(error=>{evaluate('stopWorking()');console.error(error);process.exitCode=1});
