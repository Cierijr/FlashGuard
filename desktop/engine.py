"""Sequential FFmpeg analysis; no uploads and no per-sample random seeks."""
import datetime as dt
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import time
import numpy as np

FPS = 10
WIDTH, HEIGHT = 32, 18
MERGE_GAP_SECONDS = 3.0
from checkpoint import fingerprint

def ffmpeg_path():
    configured = os.environ.get('IMAGEIO_FFMPEG_EXE')
    if configured:
        return configured
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        binary = shutil.which('ffmpeg')
        if not binary:
            raise RuntimeError('Bundled video decoder is missing. Download a complete FlashGuard package.')
        return binary

def spawn(args, **kwargs):
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(args, **kwargs)

def group_events(events, duration):
    flagged = []
    for i, first in enumerate(events):
        count, last, end = 1, first['direction'], first['t']
        for event in events[i+1:i+11]:  # at most 10 following samples in one second
            if event['t'] - first['t'] >= 1 - 1e-8:
                break
            if event['kind'] == first['kind'] and event['direction'] != last:
                count += 1
                last, end = event['direction'], event['t']
        if count >= 6:
            kind = first['kind']
            item = dict(start=max(0, first['t']-.5), end=min(duration, end+.6), patterns=[kind],
                        kind='Rapid red / light changes' if kind == 'red' else 'Rapid light changes')
            if flagged and item['start'] <= flagged[-1]['end']+MERGE_GAP_SECONDS+1e-8:
                prev = flagged[-1]
                prev['end'] = max(prev['end'], item['end'])
                prev['patterns'] = sorted(set(prev['patterns']+item['patterns']))
                prev['kind'] = 'Rapid brightness and red changes' if len(prev['patterns']) > 1 else item['kind']
            else:
                flagged.append(item)
    return flagged

class Cancelled(Exception):
    pass

class Analysis:
    def __init__(self,store=None,resume=None,checkpoint_seconds=5):
        self.cancel_event = threading.Event()
        self.lock = threading.Lock()
        self.process = None
        self.state = {'status':'idle'}
        self.store=store
        self.resume=resume
        self.checkpoint_seconds=checkpoint_seconds
        self.preserve_checkpoint=False
        self.checkpoint_data=None
        self.checkpoint_warning=None

    def update(self, **values):
        with self.lock:
            self.state.update(values)

    def snapshot(self):
        with self.lock:
            return dict(self.state)

    def pause(self):
        self.preserve_checkpoint=True
        self._interrupt()

    def cancel(self):
        self.preserve_checkpoint=False
        self._interrupt()

    def _interrupt(self):
        self.cancel_event.set()
        with self.lock:
            process = self.process
        if process and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    def run(self, filename):
        self.update(status='analyzing', frames=(self.resume or {}).get('count',0), progress=0, message='Restoring saved analysis…' if self.resume else 'Reading video details…')
        try:
            if self.store and not self.resume:
                try:
                    self.store.save(dict(schema=1,status='partial',identity=fingerprint(filename),
                        count=0,events=[],cues=[],previous=None,elapsedSeconds=0))
                except OSError:
                    self.update(checkpointWarning='Progress could not be saved. Check available disk space.')
            result = self.analyze(Path(filename))
            if self.cancel_event.is_set():
                raise Cancelled()
            if self.store:
                try:
                    self.store.save(dict(schema=1,status='complete',identity=fingerprint(filename),result=result))
                except OSError:
                    self.update(checkpointWarning='The completed report could not be saved for reopening. Download it now.')
            self.update(status='complete', progress=100, result=result)
        except Cancelled:
            if self.preserve_checkpoint:
                self.update(status='paused',message='Progress saved. Reopen FlashGuard to continue.')
            else:
                if self.store:
                    self.store.clear()
                self.update(status='cancelled', message='Analysis cancelled.')
        except Exception as error:
            self.update(status='error', message=str(error))

    def analyze(self, path):
        started = time.monotonic()
        binary = ffmpeg_path()
        # Reading the container header does not decode the full video.
        probe = spawn([binary, '-hide_banner', '-i', str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        with self.lock:
            self.process = probe
        try:
            _, metadata = probe.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            probe.kill(); probe.communicate()
            raise RuntimeError('Video metadata could not be read within 30 seconds.')
        if self.cancel_event.is_set():
            raise Cancelled()
        match = re.search(rb'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)', metadata)
        if not match:
            raise RuntimeError('Could not read video duration. Try a standard MP4 or WebM video.')
        hours, minutes, seconds = map(float, match.groups())
        duration = hours*3600+minutes*60+seconds
        if duration <= 0 or not math.isfinite(duration):
            raise RuntimeError('Video has no readable duration.')
        identity=fingerprint(path)
        saved=self.resume
        if saved and saved['identity']!=identity:
            raise RuntimeError('The video changed. Choose it again to start a new analysis.')
        events=list(saved['events']) if saved else []
        cues=list(saved['cues']) if saved else []
        count=int(saved['count']) if saved else 0
        if count<0 or count!=len(cues) or count>math.ceil(duration*FPS)+1:
            raise RuntimeError('Saved progress is invalid. Choose the video again.')
        previous=(np.asarray(saved['previous'][0],dtype=np.float32),np.asarray(saved['previous'][1],dtype=bool)) if saved and count else None
        if previous is not None and any(frame.shape!=(WIDTH*HEIGHT,) for frame in previous):
            raise RuntimeError('Saved sample state is invalid. Choose the video again.')
        resumed_count=count
        decoded=0
        elapsed_before=saved.get('elapsedSeconds',0) if saved else 0
        last_progress=0
        last_checkpoint=time.monotonic()
        if resumed_count:
            self.update(frames=count,progress=min(99,count/FPS/duration*100),message='Restoring decoder to the saved position…')
        def checkpoint():
            if not self.store or not count or previous is None:
                return
            data=dict(schema=1,status='partial',identity=identity,count=count,events=events,cues=cues,
                previous=[previous[0].tolist(),previous[1].tolist()],elapsedSeconds=elapsed_before+time.monotonic()-started)
            try:
                self.store.save(data)
                self.checkpoint_data=data
            except OSError:
                self.checkpoint_warning='Progress could not be saved. Check available disk space.'
                self.update(checkpointWarning=self.checkpoint_warning)
        with tempfile.TemporaryFile() as errors:
            process = spawn([binary, '-hide_banner', '-loglevel', 'error', '-nostdin', '-i', str(path),
                '-map', '0:v:0', '-an', '-sn', '-dn', '-vf', f'fps={FPS}:start_time=0,scale={WIDTH}:{HEIGHT}',
                '-threads', '2', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'],
                stdout=subprocess.PIPE, stderr=errors)
            with self.lock:
                self.process = process
            try:
                size = WIDTH*HEIGHT*3
                while True:
                    if self.cancel_event.is_set():
                        raise Cancelled()
                    raw = bytearray()
                    while len(raw) < size:
                        chunk = process.stdout.read(size-len(raw))
                        if not chunk:
                            break
                        raw.extend(chunk)
                    if self.cancel_event.is_set():
                        raise Cancelled()
                    if not raw:
                        break
                    if len(raw) != size:
                        raise RuntimeError('Video decoder returned an incomplete frame.')
                    decoded+=1
                    if decoded<=resumed_count:
                        continue
                    rgb = np.frombuffer(raw, dtype=np.uint8).reshape(-1,3).astype(np.float32)
                    lum = (rgb[:,0]*.2126+rgb[:,1]*.7152+rgb[:,2]*.0722)/255
                    red = (rgb[:,0] > rgb[:,1]*1.5) & (rgb[:,0] > rgb[:,2]*1.5) & (rgb[:,0] > 90)
                    t = count/FPS
                    if previous is not None:
                        old_lum, old_red = previous
                        up, down = np.mean(lum-old_lum > .1), np.mean(lum-old_lum < -.1)
                        red_up, red_down = np.mean(red & ~old_red), np.mean(~red & old_red)
                        if max(up,down,red_up,red_down) > .25:
                            use_red = max(red_up,red_down) > .25
                            events.append(dict(t=t,kind='red' if use_red else 'brightness',
                                direction=1 if (red_up>red_down if use_red else up>down) else -1))
                    previous = lum, red
                    # Keep compact frame summaries for pre-scene cues without a second decode pass.
                    cues.append((float(lum.mean()), *(float(x) for x in rgb.mean(axis=0))))
                    count += 1
                    now = time.monotonic()
                    if now-last_checkpoint>=self.checkpoint_seconds:
                        checkpoint();last_checkpoint=now
                    if now-last_progress > .2:
                        elapsed = max(.001,now-started)
                        rate = (count-resumed_count)/elapsed
                        self.update(frames=count,progress=min(99,t/duration*100),elapsedSeconds=elapsed,
                            framesPerSecond=rate,remainingSeconds=max(0,(duration*FPS-count)/rate),
                            message='Continuing saved analysis on your computer…' if resumed_count else 'Decoding and analyzing continuously on your computer…')
                        last_progress = now
                code = process.wait()
                if self.cancel_event.is_set():
                    raise Cancelled()
                if decoded<resumed_count:
                    raise RuntimeError('Video decoding ended before the saved position could be restored.')
                if code or not count:
                    errors.seek(0)
                    raise RuntimeError('Video decoding failed: '+errors.read(2000).decode(errors='replace'))
                if count/FPS < duration-.5:
                    raise RuntimeError('Video decoding ended early. No complete report was produced.')
            finally:
                if self.preserve_checkpoint or not self.cancel_event.is_set():
                    checkpoint()
                if process.poll() is None:
                    process.kill()
                process.wait()
                process.stdout.close()
                with self.lock:
                    self.process = None
        segments = group_events(events,duration)
        for segment in segments:
            t = max(0,segment['start']-1.5)
            light,r,g,b = cues[min(len(cues)-1,int(t*FPS))]
            lighting = 'a mostly dark frame' if light<.25 else 'a brightly lit frame' if light>.72 else 'a moderately lit frame'
            color = 'with muted colors' if max(r,g,b)-min(r,g,b)<20 else 'with prominent red' if r>g*1.25 and r>b*1.25 else 'with prominent blue' if b>r*1.2 and b>g*1.08 else 'with prominent green' if g>r*1.18 and g>b*1.08 else 'with mixed colors'
            segment['cue'] = f'At about {int(t)//60}:{int(t)%60:02d}, the video shows {lighting} {color}.'
        return dict(version='0.7-desktop',createdAt=dt.datetime.now(dt.timezone.utc).isoformat(),
            video=dict(name=path.name,sizeBytes=path.stat().st_size,durationSeconds=duration),
            settings=dict(sampleTargetSeconds=.1,actualSampleSpacingSeconds=.1,maxSamples=None,
                sampleWidth=32,sampleHeight=18,brightnessDeltaThreshold=.1,changedAreaFractionThreshold=.25,
                minimumAlternatingTransitions=6,windowSeconds=1,intervalPaddingBeforeSeconds=.5,
                intervalPaddingAfterSeconds=.6,mergeGapSeconds=MERGE_GAP_SECONDS,processingStrategy='sequential FFmpeg decoding',
                analyzedSamples=count,resumedSamples=resumed_count,elapsedSeconds=elapsed_before+time.monotonic()-started,
                resamplingNote='FFmpeg selects/resamples decoded frames at 10 fps; exact timestamps and scaling may differ from browser seeks.'),
            complete=True,segments=segments)


