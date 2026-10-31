// Desktop-only bridge; the repository's browser-only index.html remains usable.
let desktopPoll=null,desktopChoosing=false;
if($('desktopDownload'))$('desktopDownload').classList.add('hidden');
$('choose').textContent='Choose video (desktop analysis)';
$('drop').querySelector('strong').textContent='Choose a video from your computer';
$('drop').querySelector('small').textContent='Continuous local decoding · videos stay on this computer';
$('status').textContent='Desktop analysis ready. Choose a video to begin.';
async function desktopRequest(route){const response=await fetch(route,{method:'POST'});if(!response.ok)throw Error('Could not contact the desktop launcher.');return response.json()}
async function chooseDesktop(){if(desktopChoosing)return;desktopChoosing=true;try{const selectedFile=await desktopRequest('api/select');if(selectedFile.error)throw Error(selectedFile.error);if(selectedFile.cancelled)return;clearTimeout(desktopPoll);reset();startWorking();$('progress').classList.remove('hidden');$('details').textContent=selectedFile.name;$('details').classList.remove('hidden');player.src='video';pollDesktop()}catch(error){message(error.message)}finally{desktopChoosing=false}}
async function pollDesktop(){try{const response=await fetch('api/status');if(!response.ok)throw Error('Desktop launcher disconnected.');const state=await response.json();if(state.status==='complete'){stopWorking();reportData=state.result;segments=reportData.segments;selected=null;render(reportData.video.durationSeconds);$('saveReport').disabled=false;updateNextButton();$('summary').textContent=`Analysis complete: ${segments.length} potential flashing sections in ${fmt(reportData.video.durationSeconds)}.`;$('samplingNote').textContent=`Desktop decoding: ${reportData.settings.analyzedSamples.toLocaleString()} samples, 10 samples/sec, completed in ${reportData.settings.elapsedSeconds.toFixed(1)} seconds. Sampled analysis can miss events and does not establish safety.`;showResults();return}if(state.status==='error'||state.status==='cancelled'||state.status==='paused'){stopWorking();message(state.message);return}lastSample=state.frames||0;const progress=state.progress||0;$('bar').style.width=progress+'%';$('progress').setAttribute('aria-valuenow',Math.floor(progress));message(`${state.message||'Analyzing…'} ${progress.toFixed(1)}%`);$('heartbeat').textContent=`${state.checkpointWarning?state.checkpointWarning+' · ':''}${lastSample.toLocaleString()} frames analyzed · ${(state.framesPerSecond||0).toFixed(1)} frames/sec · remaining: ${state.remainingSeconds===undefined?'estimating…':fmt(state.remainingSeconds)}`;desktopPoll=setTimeout(pollDesktop,300)}catch(error){stopWorking();message(error.message+' Reopen FlashGuard.exe to resume saved analysis in the browser tab it opens.')}}
$('choose').onclick=chooseDesktop;
load=chooseDesktop;
$('cancel').onclick=async()=>{try{await desktopRequest('api/cancel');message('Stopping analysis…')}catch(error){message(error.message)}};


// Stable per-launcher title lets Windows select this tab without reloading the report.
document.title='FlashGuard ['+(window.FLASHGUARD_WINDOW_MARKER||'Desktop')+']';
function desktopPresence(){fetch('api/presence',{method:'POST'}).catch(()=>{});}
desktopPresence();setInterval(desktopPresence,10000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)desktopPresence()});
window.addEventListener('pagehide',()=>navigator.sendBeacon('api/disconnect'));


// Reattach automatically after reopening the EXE or reloading the report tab.
async function restoreDesktopSession(){
    try{
        const response=await fetch('api/status');
        if(!response.ok)return;
        const state=await response.json();
        if(state.status==='error'){message(state.message);return}
        if(state.videoName&&['analyzing','complete','paused'].includes(state.status)){
            clearTimeout(desktopPoll);reset();startWorking();
            $('progress').classList.remove('hidden');$('details').textContent=state.videoName;
            $('details').classList.remove('hidden');player.src='video';pollDesktop();
        }
    }catch{}
}
restoreDesktopSession();
