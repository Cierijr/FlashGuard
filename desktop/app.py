"""Loopback-only desktop launcher. Uses the existing FlashGuard review interface."""
import json
import mimetypes
import os
from pathlib import Path
import queue
import re
import secrets
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import webbrowser
from engine import Analysis, ffmpeg_path
from launcher import Launcher

ASSETS = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))

class Desktop:
    def __init__(self, root):
        self.root = root
        self.requests = queue.Queue()
        self.analysis = Analysis()
        self.filename = None
        self.thread = None
        self.token = secrets.token_urlsafe(32)
        self.server = None

    def choose(self):
        if self.thread and self.thread.is_alive():
            return {'error':'Cancel the current analysis and wait for it to stop before selecting another video.'}
        result = queue.Queue()
        self.requests.put(result)
        filename = result.get()
        if not filename:
            return {'cancelled':True}
        self.filename = Path(filename)
        self.analysis = Analysis()
        self.thread = threading.Thread(target=self.analysis.run,args=(filename,),daemon=True)
        self.thread.start()
        return {'selected':True,'name':self.filename.name}

    def dialogs(self):
        try:
            result = self.requests.get_nowait()
            try:
                self.root.attributes('-topmost', True)
                path = filedialog.askopenfilename(parent=self.root,title='Choose a video for FlashGuard',
                    filetypes=[('Video files','*.mp4 *.webm *.mov *.mkv *.avi *.m4v'),('All files','*.*')])
                result.put(path)
            except Exception:
                result.put('')
            finally:
                self.root.attributes('-topmost',False)
        except queue.Empty:
            pass
        self.root.after(100,self.dialogs)

    def request_close(self):
        active = self.thread is not None and self.thread.is_alive()
        if active and not messagebox.askyesno('Stop analysis and exit?',
            'A video is still being analyzed. Closing FlashGuard stops the analysis.\n\nExit anyway? You can minimize this window instead.', parent=self.root):
            return
        self.stop()

    def stop(self):
        self.analysis.cancel()
        self.root.quit()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass

    def authorized(self):
        app = self.server.app
        host = self.headers.get('Host')
        origin = self.headers.get('Origin')
        expected = f'127.0.0.1:{self.server.server_port}'
        return host == expected and (not origin or origin == 'http://'+expected) and self.path.startswith('/'+app.token+'/')

    def reply(self,data,status=200,kind='application/json'):
        if not isinstance(data,bytes):
            data = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):
            pass

    def do_GET(self):
        if not self.authorized():
            return self.reply({'error':'Not found'},404)
        route = self.path.split('?',1)[0].split('/',2)[2]
        app = self.server.app
        if route == '':
            html = (ASSETS/'index.html').read_text(encoding='utf-8')
            bridge = (ASSETS/'desktop'/'bridge.js').read_text(encoding='utf-8')
            html = html.replace('</body>', '<script>'+bridge+'</script></body>')
            return self.reply(html.encode(),kind='text/html; charset=utf-8')
        if route == 'api/status':
            return self.reply(app.analysis.snapshot())
        if route == 'video' and app.filename:
            return self.video(app.filename)
        self.reply({'error':'Not found'},404)

    def do_POST(self):
        if not self.authorized():
            return self.reply({'error':'Not found'},404)
        route = self.path.split('/',2)[2]
        app = self.server.app
        if route == 'api/select':
            return self.reply(app.choose())
        if route == 'api/cancel':
            app.analysis.cancel()
            return self.reply({'cancelled':True})
        self.reply({'error':'Not found'},404)

    def video(self,path):
        size = path.stat().st_size
        start,end = 0,size-1
        header = self.headers.get('Range')
        if header:
            match = re.fullmatch(r'bytes=(\d+)-(\d*)',header)
            if not match:
                return self.reply({'error':'Unsupported range'},416)
            start = int(match[1]);end = min(size-1,int(match[2])) if match[2] else size-1
            if start>end or start>=size:
                return self.reply({'error':'Range outside video'},416)
        self.send_response(206 if header else 200)
        self.send_header('Content-Type',mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        self.send_header('Accept-Ranges','bytes')
        self.send_header('Content-Length',str(end-start+1))
        if header:
            self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        try:
            with path.open('rb') as source:
                source.seek(start)
                remaining = end-start+1
                while remaining:
                    data = source.read(min(1024*1024,remaining))
                    if not data:
                        break
                    self.wfile.write(data)
                    remaining -= len(data)
        except (BrokenPipeError,ConnectionResetError):
            pass

def main():
    if '--self-test' in sys.argv:
        import subprocess
        result = subprocess.run([ffmpeg_path(),'-version'],capture_output=True,check=True)
        assert b'ffmpeg version' in result.stdout
        # Also exercise the packaged native launcher; no browser or video plays.
        root = tk.Tk()
        app = Desktop(root)
        launcher = Launcher(root,app,lambda:None)
        root.update()
        launcher.toggle(); launcher.pong.step(.03); launcher.draw()
        launcher.pause(); root.update(); root.destroy()
        assert (ASSETS/'index.html').exists() and (ASSETS/'desktop'/'bridge.js').exists()
        return
    root = tk.Tk()
    root.title('FlashGuard Desktop')
    app = Desktop(root)
    server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server.app = app
    app.server = server
    address = f'http://127.0.0.1:{server.server_port}/{app.token}/'
    launcher = Launcher(root,app,lambda:webbrowser.open(address))
    root.protocol('WM_DELETE_WINDOW',app.request_close)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    root.after(100,app.dialogs)
    root.after(500,lambda:webbrowser.open(address))
    try:
        root.mainloop()
    finally:
        app.analysis.cancel()
        server.shutdown()
        server.server_close()
        root.destroy()

if __name__ == '__main__':
    main()
