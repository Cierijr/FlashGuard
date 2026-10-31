import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from http.server import ThreadingHTTPServer
from engine import Analysis, ffmpeg_path, spawn, group_events
from app import Handler, Desktop
from launcher import Launcher
from checkpoint import SessionStore, fingerprint
from unittest.mock import Mock, patch

class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name)/'long-video.mp4'
        process = spawn([ffmpeg_path(),'-v','error','-y','-f','rawvideo','-pixel_format','rgb24',
            '-video_size','32x18','-framerate','10','-i','pipe:0','-an','-c:v','libx264',
            '-preset','ultrafast','-g','30',str(cls.path)],stdin=subprocess.PIPE)
        for index in range(7200):
            t=index/10
            flashing=5<=t<6 or 359.5<=t<360.5 or 700<=t<701
            value=255 if flashing and index%2 else 0
            process.stdin.write(bytes([value])*(32*18*3))
        process.stdin.close()
        assert process.wait()==0

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_actual_long_video(self):
        job=Analysis();start=time.monotonic();job.run(self.path)
        state=job.snapshot()
        self.assertEqual(state['status'],'complete',state)
        report=state['result']
        self.assertEqual(report['settings']['analyzedSamples'],7200)
        for t in (5.5,360,700.5):
            self.assertTrue(any(s['start']<=t<=s['end'] for s in report['segments']),t)
        self.assertTrue(all('cue' in s for s in report['segments']))
        print(f"Real 12-minute video: {report['settings']['analyzedSamples']} samples in {time.monotonic()-start:.2f}s (32x18 test fixture, not a full-resolution benchmark).")

    def test_invalid_and_cancel(self):
        path=Path(self.temp.name)/'invalid.mp4';path.write_text('not a video')
        job=Analysis();job.run(path)
        self.assertEqual(job.snapshot()['status'],'error')
        job=Analysis();job.cancel();job.run(self.path)
        self.assertEqual(job.snapshot()['status'],'cancelled')
        job=Analysis();thread=threading.Thread(target=job.run,args=(self.path,));thread.start()
        limit=time.monotonic()+5
        while job.snapshot().get('frames',0)<20 and thread.is_alive() and time.monotonic()<limit:
            time.sleep(.005)
        job.cancel();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual(job.snapshot()['status'],'cancelled')

    def test_merge_nearby_flashing_bursts(self):
        def burst(start,kind='brightness'):
            return [dict(t=start+i*.1,kind=kind,direction=1 if i%2 else -1) for i in range(8)]
        result=group_events(burst(1)+burst(5,'red'),20)
        self.assertEqual(len(result),1,'brief gaps in the same flashing sequence are grouped')
        self.assertEqual(result[0]['patterns'],['brightness','red'])
        self.assertLessEqual(result[0]['start'],1)
        self.assertGreaterEqual(result[0]['end'],5.7)
        self.assertEqual(len(group_events(burst(1)+burst(10),20)),2,'distant sequences remain separate')
        self.assertEqual(group_events([dict(t=1,kind='brightness',direction=1)],20),[])

    def test_browser_button_reuses_existing_tab(self):
        app=Desktop(SimpleNamespace(quit=Mock()))
        app.address='http://127.0.0.1:12345/test/'
        def wait():
            limit=time.monotonic()+2
            while app.browser_lock.locked() and time.monotonic()<limit:
                time.sleep(.005)
            self.assertFalse(app.browser_lock.locked())
        with patch('app.focus_existing',return_value=True) as focus, patch('app.webbrowser.open') as opened:
            app.open_browser();wait();focus.assert_called_once();opened.assert_not_called()
        app.browser_seen=time.monotonic()
        with patch('app.focus_existing',return_value=False), patch('app.webbrowser.open') as opened:
            app.open_browser();wait();opened.assert_not_called()
            self.assertIn('no duplicate',app.browser_message)
        app.browser_seen=0;app.last_browser_launch=0
        with patch('app.focus_existing',return_value=False), patch('app.webbrowser.open') as opened:
            app.open_browser();wait();opened.assert_called_once_with(app.address)
            app.open_browser();wait();opened.assert_called_once()

    def test_close_confirmation_during_analysis(self):
        app=Desktop(SimpleNamespace(quit=Mock()))
        app.thread=SimpleNamespace(is_alive=lambda:True)
        app.stop=Mock()
        with patch('app.messagebox.askyesno',return_value=False):
            app.request_close();app.stop.assert_not_called()
        with patch('app.messagebox.askyesno',return_value=True):
            app.request_close();app.stop.assert_called_once()
        app.stop.reset_mock();app.thread=None
        with patch('app.messagebox.askyesno') as question:
            app.request_close();question.assert_not_called();app.stop.assert_called_once()

    def test_saved_analysis_resumes_without_gaps_or_duplicate_samples(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SessionStore(folder)
            zero=Analysis(store=store);zero.pause();zero.run(self.path)
            self.assertEqual(store.load()['count'],0,'closing during metadata must still preserve the selected video')
            store.clear()
            interrupted=Analysis(store=store)
            update=interrupted.update
            def pause_after_progress(**values):
                update(**values)
                if values.get('frames',0)>=100 and not interrupted.cancel_event.is_set():
                    interrupted.pause()
            interrupted.update=pause_after_progress
            interrupted.run(self.path)
            self.assertEqual(interrupted.snapshot()['status'],'paused',interrupted.snapshot())
            saved=SessionStore(folder).load()
            self.assertIsNotNone(saved)
            self.assertGreater(saved['count'],0)
            resumed=Analysis(store=store,resume=saved);resumed.run(self.path)
            state=resumed.snapshot()
            self.assertEqual(state['status'],'complete',state)
            full=Analysis();full.run(self.path)
            self.assertEqual(state['result']['segments'],full.snapshot()['result']['segments'])
            self.assertEqual(state['result']['settings']['analyzedSamples'],7200)
            self.assertEqual(state['result']['settings']['resumedSamples'],saved['count'])
            app=Desktop(SimpleNamespace(quit=Mock()),store=SessionStore(folder))
            app.restore_session()
            self.assertEqual(app.analysis.snapshot()['status'],'complete')
            self.assertIsNone(app.thread,'completed sessions restore without restarting analysis')

    def test_forced_process_exit_recovers_last_atomic_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            code="""import sys,time
from checkpoint import SessionStore
from engine import Analysis
class SaveThenWait(SessionStore):
    def save(self,data):
        super().save(data)
        if data['status']=='partial' and data['count']>0:
            time.sleep(30)
Analysis(store=SaveThenWait(sys.argv[2]),checkpoint_seconds=.05).run(sys.argv[1])
"""
            process=spawn([sys.executable,'-c',code,str(self.path),folder],cwd=Path(__file__).parent,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            store=SessionStore(folder)
            try:
                limit=time.monotonic()+15
                saved=None
                while process.poll() is None and time.monotonic()<limit:
                    saved=store.load()
                    if saved and saved.get('count',0)>0:
                        break
                    time.sleep(.02)
                self.assertIsNotNone(saved,'child must persist a checkpoint before termination')
                self.assertGreater(saved.get('count',0),0)
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
            saved=store.load();self.assertIsNotNone(saved)
            resumed=Analysis(store=store,resume=saved);resumed.run(self.path)
            state=resumed.snapshot();self.assertEqual(state['status'],'complete',state)
            self.assertEqual(state['result']['settings']['analyzedSamples'],7200)
            for t in (5.5,360,700.5):
                self.assertTrue(any(s['start']<=t<=s['end'] for s in state['result']['segments']))

    def test_checkpoint_validation_cancel_and_single_instance(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SessionStore(folder)
            store.path.write_bytes(b'not a saved checkpoint')
            self.assertIsNone(store.load());self.assertIsNotNone(store.warning)
            identity=fingerprint(self.path)
            store.save(dict(schema=1,status='partial',identity={**identity,'size':identity['size']+1}))
            self.assertIsNone(store.load(),'changed video identity must not resume')
            store.save(dict(schema=1,status='partial',identity=identity,count=1))
            job=Analysis(store=store);job.cancel();job.run(self.path)
            self.assertFalse(store.path.exists(),'explicit cancellation discards saved progress')
            self.assertTrue(store.acquire())
            second=SessionStore(folder)
            self.assertFalse(second.acquire(),'only one launcher may write the shared session')
            store.release();self.assertTrue(second.acquire());second.release()

    def test_loopback_api_and_range(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        server.app=SimpleNamespace(token='test-token',browser_marker='FG-test',filename=self.path,analysis=Analysis())
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        connection=http.client.HTTPConnection('127.0.0.1',server.server_port)
        try:
            connection.request('GET','/test-token/')
            response=connection.getresponse();html=response.read();self.assertEqual(response.status,200)
            self.assertIn(b'chooseDesktop',html)
            connection.request('GET','/wrong/api/status')
            response=connection.getresponse();response.read();self.assertEqual(response.status,404)
            connection.request('GET','/test-token/api/status',headers={'Origin':'https://example.com'})
            response=connection.getresponse();response.read();self.assertEqual(response.status,404)
            connection.request('GET','/test-token/video',headers={'Range':'bytes=0-99'})
            response=connection.getresponse();data=response.read();self.assertEqual(response.status,206)
            self.assertEqual(data,self.path.read_bytes()[:100])
            connection.request('GET','/test-token/api/status')
            response=connection.getresponse();self.assertEqual(json.loads(response.read())['status'],'idle')
        finally:
            connection.close();server.shutdown();server.server_close()

if __name__=='__main__':
    unittest.main()


