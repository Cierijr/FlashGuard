const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/index.html','utf8');const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const ids=[...html.matchAll(/id="([^"]+)"/g)].map(x=>x[1]);assert.equal(new Set(ids).size,ids.length);
for(const [,id] of js.matchAll(/\$\('([^']+)'\)/g))assert(ids.includes(id),id);
function fakeNode(){const classes=new Set(),listeners={};return {children:[],attrs:{},classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),contains:x=>classes.has(x),toggle(x,force){if(force===true)classes.add(x);else if(force===false)classes.delete(x);else if(classes.has(x))classes.delete(x);else classes.add(x)}},style:{},value:'',paused:true,currentTime:0,readyState:4,seeking:false,playbackRate:1,addEventListener(name,fn){(listeners[name]??=[]).push(fn)},removeEventListener(name,fn){listeners[name]=(listeners[name]||[]).filter(f=>f!==fn)},emit(name){for(const fn of listeners[name]||[])fn()},setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]},load(){},focus(){this.focused=true},append(...items){this.children.push(...items)},click(){this.onclick?.()},remove(){},querySelector(name){return this.parts??=Object.create(null),this.parts[name]??=fakeNode()},pause(){this.paused=true;this.onpause?.()},async play(){this.paused=false;this.onplay?.()},getContext(){return {drawImage(){},getImageData(){return {data:new Uint8Array(576*4)}}}},_text:'',get textContent(){return this._text},set textContent(v){this._text=v;this.children=[]},get innerHTML(){return this._html||''},set innerHTML(v){this._html=v;this.children=[]}}}
const elements={};for(const id of ids){const node=fakeNode();const markup=html.match(new RegExp('<[^>]*id="'+id+'"[^>]*>'))?.[0]||'';for(const c of markup.match(/class="([^"]*)"/)?.[1].split(' ')||[])node.classList.add(c);node.value={brightness:'50',speed:'1',patternFilter:'all',playbackMode:'preview',exportFormat:'text'}[id]||'';elements[id]=node}
const body=fakeNode(),created=[];const context=vm.createContext({document:{body,getElementById:id=>elements[id],querySelectorAll:selector=>selector==='.segment'?elements.segments.children.filter(n=>n.className==='segment'):[],createElement:tag=>{const n=fakeNode();n.tag=tag;created.push(n);return n}},console,Float32Array,Uint8Array,Blob,URL:{revokeObjectURL(){},createObjectURL:()=> 'blob:report'},setTimeout,clearTimeout,setInterval,clearInterval,requestAnimationFrame:()=>1,cancelAnimationFrame(){}});vm.runInContext(js,context);
const evaluate=s=>vm.runInContext(s,context);
const events=(times,kind='brightness')=>times.map((t,i)=>({t,kind,direction:i%2?1:-1}));context.single=events([0,.2,.4]);assert.equal(evaluate('groupFlashEvents(single,10).length'),0,'isolated movement does not count as repeated flashes');
context.flash=events([1,1.1,1.2,1.3,1.4,1.5]);assert.equal(evaluate('groupFlashEvents(flash,10).length'),1);
context.monotonic=Array.from({length:8},(_,i)=>({t:i*.1,kind:'brightness',direction:1}));assert.equal(evaluate('groupFlashEvents(monotonic,10).length'),0);
context.near=[...events([1,1.1,1.2,1.3,1.4,1.5]),...events([3,3.1,3.2,3.3,3.4,3.5])];assert.equal(evaluate('groupFlashEvents(near,10).length'),1);
context.far=[...events([1,1.1,1.2,1.3,1.4,1.5]),...events([6,6.1,6.2,6.3,6.4,6.5])];assert.equal(evaluate('groupFlashEvents(far,10).length'),2);
context.red=events([1,1.1,1.2,1.3,1.4,1.5],'red');assert.match(evaluate('groupFlashEvents(red,10)[0].kind'),/red/);
evaluate("reportData={complete:true,video:{durationSeconds:10}};segments=[{start:1,end:2}];selected=0;clipEnd=2;player.currentTime=1;$('veil').classList.add('hidden');togglePreview()");assert.equal(elements.player.paused,false);elements.player.onclick();assert.equal(elements.player.paused,true);assert.match(elements.playState.textContent,/Paused/);elements.player.onclick();assert.equal(elements.player.paused,false);
elements.player.currentTime=2;elements.player.ontimeupdate();assert.equal(elements.player.paused,true);elements.player.onclick();assert.equal(elements.player.currentTime,1);
elements.brightness.value='30';elements.brightness.oninput();assert.equal(elements.player.style.filter,'brightness(30%)');elements.speed.value='.5';elements.speed.onchange();assert.equal(elements.player.playbackRate,.5);
evaluate('showResults()');assert(elements.homeView.classList.contains('hidden'));evaluate('showHome()');assert(elements.resultsView.classList.contains('hidden'));assert.equal(elements.player.paused,true);
assert(!/<script[^>]+src=|<link[^>]+href=/.test(html));console.log('PASS: DOM integrity; movement/monotonic rejection; brightness/red repetitions; nearby/separate grouping; click pause/resume/replay; endpoint stop; dimming/speed; home/results navigation; embedded assets.');

// Five October 23 features, including boundaries and complete-report exports.
assert.equal(evaluate('nextFlagIndex(0,[{start:0,end:1}],null)'),0);assert.equal(evaluate("parseTimestamp('1:23.5')"),83.5);assert.equal(evaluate("parseTimestamp('1:02:03')"),3723);for(const v of ['', '1:70','-2','bad','1.2:30']){context.badTime=v;assert.equal(evaluate('parseTimestamp(badTime)'),null)}
evaluate("segments=[{start:1,end:2,kind:'Rapid light changes',patterns:['brightness'],cue:'Dark frame'},{start:4,end:5,kind:'Rapid red / light changes',patterns:['red'],cue:'Red frame'}];reportData={complete:true,createdAt:'test',video:{name:'test.mp4',durationSeconds:10},settings:{maxSamples:3600,actualSampleSpacingSeconds:.1}};notes=[];selected=null;playMode='preview';player.currentTime=0;render(10);updateNextButton()");
assert.equal(elements.nextFlag.disabled,false);elements.nextFlag.onclick();assert.equal(evaluate('selected'),0);assert.equal(elements.player.paused,true);assert(!elements.veil.classList.contains('hidden'));elements.nextFlag.onclick();assert.equal(evaluate('selected'),1);assert.equal(elements.nextFlag.disabled,true);
elements.patternFilter.value='red';elements.patternFilter.onchange();assert(elements.segments.children[0].classList.contains('hidden'));assert(!elements.segments.children[1].classList.contains('hidden'));
elements.findTime.value='3';elements.findFlag.onclick();assert.equal(evaluate('selected'),1);assert.equal(elements.player.paused,true);elements.findTime.value='20';elements.findFlag.onclick();assert.match(elements.filterStatus.textContent,/within this video/);
elements.noteTime.value='0:03.250';elements.noteText.value='<img src=x onerror=alert(1)> review';elements.addNote.onclick();assert.equal(evaluate('notes[0].timeSeconds'),3.25);assert.equal(elements.notesList.children[0].children[0].textContent,'0:03.250 — <img src=x onerror=alert(1)> review');assert.equal(elements.notesList.children[0].children[0].innerHTML,'');
const data=evaluate('exportReport()');assert.equal(data.flaggedIntervals.length,2,'filter does not remove saved flags');assert.equal(data.settings.maxSamples,3600);assert.equal(data.manualNotes.length,1);context.savedData=data;assert.match(evaluate('reportText(savedData)'),/0:03.250/);assert.match(evaluate('reportText(savedData)'),/actualSampleSpacingSeconds/);
elements.exportFormat.value='json';elements.saveReport.onclick();assert.equal(created.at(-1).download,'FlashGuard-report.json');elements.exportFormat.value='text';elements.saveReport.onclick();assert.equal(created.at(-1).download,'FlashGuard-report.txt');
assert.equal(evaluate('nextUnflaggedTime(1,segments,10)'),2.08);assert.equal(evaluate('nextUnflaggedTime(3,segments,10)'),3);assert.equal(evaluate('nextUnflaggedTime(.95,segments,10)'),2.08);assert.equal(evaluate('nextUnflaggedTime(9,[{start:8,end:10}],10)'),10);assert.equal(evaluate('nextUnflaggedTime(1,[{start:1,end:2},{start:2.05,end:3}],10)'),3.08);
elements.startSkip.onclick();assert.equal(evaluate('playMode'),'skip');assert.equal(elements.player.paused,true);assert(!elements.veil.classList.contains('hidden'));evaluate("$('veil').classList.add('hidden');player.currentTime=1;player.paused=false;enforceBoundary()");assert.equal(elements.player.currentTime,2.08,'skip uses brightness flag even with red list filter');assert(!elements.skipShield.classList.contains('hidden'));elements.player.emit('seeked');assert(elements.skipShield.classList.contains('hidden'));
evaluate('player.currentTime=3;selected=null');elements.nextFlag.onclick();assert.equal(evaluate('selected'),1);assert.equal(evaluate('playMode'),'preview');assert.equal(elements.player.paused,true);assert(!elements.veil.classList.contains('hidden'));
evaluate('reset()');assert.equal(evaluate('notes.length'),0);assert.equal(evaluate('reportData'),null);assert.equal(elements.saveReport.disabled,true);assert.equal(elements.nextFlag.disabled,true);
console.log('PASS: timestamp parsing, next warning with consent, pattern filtering, find, safe note rendering, complete exports and settings, skip boundaries/end/adjacent intervals, mode switching, and reset.');
// Exercise the actual entry points, not just individual playback controls.
(async()=>{
  assert.doesNotThrow(()=>evaluate('reset()'),'choosing a file must reset without undefined progress variables');
  await evaluate("load({name:'notes.txt',type:'text/plain'})");
  assert.equal(elements.status.textContent,'Choose a video file.');
  context.URL.createObjectURL=()=> 'blob:test-video';
  elements.analyzer.duration=2;
  evaluate("waitForMetadata=async()=>{};analyze=async(duration,id)=>{globalThis.analysisStarted={duration,id};stopWorking()}");
  await evaluate("load({name:'clip.mp4',type:'video/mp4',size:1024})");
  assert.equal(context.analysisStarted.duration,2,'valid video reaches analysis');
  assert.equal(elements.analyzer.src,'blob:test-video');
  assert.equal(elements.player.src,'blob:test-video');
  assert.equal(elements.player.paused,true,'choosing video must not autoplay preview');
  elements.file.files=[{name:'second.webm',type:'video/webm',size:2048}];
  elements.file.onchange();await new Promise(resolve=>setImmediate(resolve));
  assert.equal(context.analysisStarted.id,evaluate('run'),'file selection starts current analysis');
  elements.cancel.onclick();assert.equal(elements.status.textContent,'Analysis cancelled. Choose a video to start again.');
  assert.equal(evaluate('busy'),false);
  // Restore the real analysis function and run it over simulated constant decoded frames.
  evaluate('analyze='+js.match(/async function analyze[\s\S]*?(?=async function describeApproaches)/)[0]);
  evaluate("seek=async()=>{};waitForMetadata=async()=>{}");
  elements.analyzer.duration=.3;
  await evaluate("load({name:'constant.mp4',type:'video/mp4',size:100})");
  assert.equal(evaluate('reportData.complete'),true);
  assert.equal(evaluate('segments.length'),0);
  assert.equal(elements.saveReport.disabled,false);
  assert.equal(elements.progress.attrs['aria-valuenow'],'100');
  assert(!elements.resultsView.classList.contains('hidden'));
  console.log('PASS: reset, invalid file, valid-video loading, file-change handler, no preview autoplay, and cancellation.');
})().catch(e=>{console.error(e);process.exitCode=1});
