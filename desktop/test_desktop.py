import http.client
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from http.server import ThreadingHTTPServer
from engine import Analysis, ffmpeg_path, spawn, group_events
from app import Handler, Desktop
from launcher import Pong, Launcher
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

    def test_pong_pause_collisions_and_scoring(self):
        game=Pong();game.step(.03);self.assertEqual((game.x,game.y),(300,95))
        game.playing=True;game.x=31;game.y=game.paddle;game.vx=-150
        game.step(.02);self.assertGreater(game.vx,0)
        game.y=7;game.vy=-70;game.step(.02);self.assertGreater(game.vy,0)
        game.x=-1;game.y=10;game.vx=-150;game.step(.02)
        self.assertEqual(game.opponent_score,1);self.assertEqual(game.x,300)
        game.move(-100);self.assertEqual(game.paddle,24)
        game.move(1000);self.assertEqual(game.paddle,166)
        game.x=300;game.vx=150;game.step(10);self.assertLessEqual(game.x,307.5)
        game.playing=False;before=(game.x,game.y);game.step(.03)
        self.assertEqual((game.x,game.y),before)

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

    def test_launcher_live_progress_and_completion(self):
        view=Launcher.__new__(Launcher)
        view.root=SimpleNamespace(after=Mock())
        view.status=Mock();view.filename=Mock();view.detail=Mock();view.progress={}
        view.last_status=None;view.pause=Mock()
        state={'status':'analyzing','progress':42,'frames':420,'remainingSeconds':15}
        view.app=SimpleNamespace(filename=Path('sample.mp4'),analysis=SimpleNamespace(snapshot=lambda:state))
        view.refresh();self.assertEqual(view.progress['value'],42)
        self.assertIn('420 frames',view.detail.configure.call_args.kwargs['text'])
        state.update(status='complete',progress=100)
        view.refresh();view.pause.assert_called_once()
        self.assertIn('browser',view.detail.configure.call_args.kwargs['text'])
        view.refresh();view.pause.assert_called_once()

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

