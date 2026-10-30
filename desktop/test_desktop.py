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
from engine import Analysis, ffmpeg_path, spawn
from app import Handler

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

    def test_loopback_api_and_range(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        server.app=SimpleNamespace(token='test-token',filename=self.path,analysis=Analysis())
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
