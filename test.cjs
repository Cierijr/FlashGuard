const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/index.html','utf8');const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const ids=[...html.matchAll(/id="([^"]+)"/g)].map(x=>x[1]);assert.equal(new Set(ids).size,ids.length);
for(const [,id] of js.matchAll(/\$\('([^']+)'\)/g))assert(ids.includes(id),id);
const elements={};for(const id of ids){const classes=new Set((html.match(new RegExp('<[^>]*id="'+id+'"[^>]*>'))?.[0].match(/class="([^"]*)"/)?.[1]||'').split(' '));elements[id]={classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),contains:x=>classes.has(x),toggle(){}},style:{},value:id==='brightness'?'50':'1',paused:true,currentTime:0,readyState:4,seeking:false,playbackRate:1,addEventListener(){},removeEventListener(){},setAttribute(){},removeAttribute(){},load(){},focus(){},append(){},pause(){this.paused=true;this.onpause?.()},async play(){this.paused=false;this.onplay?.()},getContext(){return {}},textContent:''};}
const context=vm.createContext({document:{getElementById:id=>elements[id],querySelectorAll:()=>[],createElement:()=>({})},console,Float32Array,Uint8Array,URL:{revokeObjectURL(){}},setTimeout,clearTimeout,setInterval,clearInterval,requestAnimationFrame:()=>1,cancelAnimationFrame(){}});vm.runInContext(js,context);
const evaluate=s=>vm.runInContext(s,context);
const events=(times,kind='brightness')=>times.map((t,i)=>({t,kind,direction:i%2?1:-1}));context.single=events([0,.2,.4]);assert.equal(evaluate('groupFlashEvents(single,10).length'),0,'isolated movement does not count as repeated flashes');
context.flash=events([1,1.1,1.2,1.3,1.4,1.5]);assert.equal(evaluate('groupFlashEvents(flash,10).length'),1);
context.monotonic=Array.from({length:8},(_,i)=>({t:i*.1,kind:'brightness',direction:1}));assert.equal(evaluate('groupFlashEvents(monotonic,10).length'),0);
context.near=[...events([1,1.1,1.2,1.3,1.4,1.5]),...events([3,3.1,3.2,3.3,3.4,3.5])];assert.equal(evaluate('groupFlashEvents(near,10).length'),1);
context.far=[...events([1,1.1,1.2,1.3,1.4,1.5]),...events([6,6.1,6.2,6.3,6.4,6.5])];assert.equal(evaluate('groupFlashEvents(far,10).length'),2);
context.red=events([1,1.1,1.2,1.3,1.4,1.5],'red');assert.match(evaluate('groupFlashEvents(red,10)[0].kind'),/red/);
evaluate("segments=[{start:1,end:2}];selected=0;clipEnd=2;player.currentTime=1;$('veil').classList.add('hidden');togglePreview()");assert.equal(elements.player.paused,false);elements.player.onclick();assert.equal(elements.player.paused,true);assert.match(elements.playState.textContent,/Paused/);elements.player.onclick();assert.equal(elements.player.paused,false);
elements.player.currentTime=2;elements.player.ontimeupdate();assert.equal(elements.player.paused,true);elements.player.onclick();assert.equal(elements.player.currentTime,1);
elements.brightness.value='30';elements.brightness.oninput();assert.equal(elements.player.style.filter,'brightness(30%)');elements.speed.value='.5';elements.speed.onchange();assert.equal(elements.player.playbackRate,.5);
evaluate('showResults()');assert(elements.homeView.classList.contains('hidden'));evaluate('showHome()');assert(elements.resultsView.classList.contains('hidden'));assert.equal(elements.player.paused,true);
assert(!/<script[^>]+src=|<link[^>]+href=/.test(html));console.log('PASS: DOM integrity; movement/monotonic rejection; brightness/red repetitions; nearby/separate grouping; click pause/resume/replay; endpoint stop; dimming/speed; home/results navigation; embedded assets.');
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
  console.log('PASS: reset, invalid file, valid-video loading, file-change handler, no preview autoplay, and cancellation.');
})().catch(e=>{console.error(e);process.exitCode=1});
