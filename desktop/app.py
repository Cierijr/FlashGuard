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
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import webbrowser
from checkpoint import SessionStore
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from engine import Analysis, ffmpeg_path
from launcher import Launcher
from browser_focus import focus_existing

ASSETS = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))

class Desktop:
    def __init__(self, root, store=None):
        self.root = root
        self.requests = queue.Queue()
        self.notifications = queue.Queue()
        self.store=store or SessionStore()
        self.analysis = Analysis(store=self.store)
        self.filename = None
        self.thread = None
        self.token = secrets.token_urlsafe(32)
        self.server = None
        self.browser_marker = 'FG-'+secrets.token_hex(6)
        self.browser_seen = 0.0
        self.last_browser_launch = 0.0
        self.browser_lock = threading.Lock()
        self.browser_message = 'Use this button to return to your report tab.'
        self.address = None

    def open_browser(self):
        if not self.browser_lock.acquire(blocking=False):
            return
        self.browser_message = 'Finding your FlashGuard tab…'
        def navigate():
            try:
                if focus_existing(self.browser_marker):
                    self.browser_message = 'Returned to your existing FlashGuard tab.'
                elif max(self.browser_seen,self.last_browser_launch)>0 and time.monotonic()-max(self.browser_seen,self.last_browser_launch)<120:
                    self.browser_message = 'Your tab is open. Select FlashGuard in your browser; no duplicate was opened.'
                    self.notifications.put(self.browser_message)
                else:
                    webbrowser.open(self.address)
                    self.last_browser_launch = time.monotonic()
                    self.browser_message = 'FlashGuard opened in your browser.'
            finally:
                self.browser_lock.release()
        threading.Thread(target=navigate,daemon=True).start()

    def restore_session(self):
        saved=self.store.load()
        if not saved:
            if self.store.warning:
                self.analysis.update(status='error',message=self.store.warning)
            return
        self.filename=Path(saved['identity']['path'])
        if saved['status']=='complete':
            self.analysis.update(status='complete',progress=100,result=saved['result'])
        else:
            self.analysis=Analysis(store=self.store,resume=saved)
            self.thread=threading.Thread(target=self.analysis.run,args=(self.filename,),daemon=True)
            self.thread.start()

    def choose(self):
        if self.thread and self.thread.is_alive():
            return {'error':'Cancel the current analysis and wait for it to stop before selecting another video.'}
        result = queue.Queue()
        self.requests.put(result)
        filename = result.get()
        if not filename:
            return {'cancelled':True}
        self.filename = Path(filename)
        self.store.clear()
        self.analysis = Analysis(store=self.store)
        self.thread = threading.Thread(target=self.analysis.run,args=(filename,),daemon=True)
        self.thread.start()
        return {'selected':True,'name':self.filename.name}

    def dialogs(self):
        try:
            result = self.requests.get_nowait()
            was_minimized=False
            try:
                was_minimized=self.root.state()=='iconic'
                if was_minimized:
                    self.root.deiconify()
                self.root.attributes('-topmost', True)
                path = filedialog.askopenfilename(parent=self.root,title='Choose a video for FlashGuard',
                    filetypes=[('Video files','*.mp4 *.webm *.mov *.mkv *.avi *.m4v'),('All files','*.*')])
                result.put(path)
            except Exception:
                result.put('')
            finally:
                self.root.attributes('-topmost',False)
                if was_minimized:
                    self.root.iconify()
        except queue.Empty:
            pass
        try:
            message=self.notifications.get_nowait()
            messagebox.showinfo('Return to FlashGuard',message,parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100,self.dialogs)

    def request_close(self):
        active = self.thread is not None and self.thread.is_alive()
        if active and not messagebox.askyesno('Save progress and exit?',
            'A video is still being analyzed. FlashGuard will save progress and pause. Reopen FlashGuard.exe to continue.\n\nSave and exit? You can minimize this window instead.', parent=self.root):
            return
        self.stop()

    def stop(self):
        self.analysis.pause()
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
            html = html.replace('</body>', '<script>window.FLASHGUARD_WINDOW_MARKER='+json.dumps(app.browser_marker)+';</script><script>'+bridge+'</script></body>')
            return self.reply(html.encode(),kind='text/html; charset=utf-8')
        if route == 'api/status':
            state=app.analysis.snapshot()
            state['videoName']=app.filename.name if app.filename else None
            return self.reply(state)
        if route == 'video' and app.filename:
            return self.video(app.filename)
        self.reply({'error':'Not found'},404)

    def do_POST(self):
        if not self.authorized():
            return self.reply({'error':'Not found'},404)
        route = self.path.split('/',2)[2]
        app = self.server.app
        if route == 'api/return':
            app.open_browser()
            return self.reply({'ok':True})
        if route == 'api/disconnect':
            app.browser_seen = 0.0
            app.last_browser_launch = 0.0
            return self.reply({'connected':False})
        if route == 'api/presence':
            app.browser_seen = time.monotonic()
            return self.reply({'connected':True})
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
        root.withdraw()
        app = Desktop(root)
        launcher = Launcher(root,app,lambda:None)
        root.update()
        assert launcher.return_button.cget('text')=='Return to FlashGuard tab'
        assert len(root.winfo_children())==1
        root.iconify();root.update()
        if os.name=='nt':
            assert root.state()=='iconic'
        root.destroy()
        assert Path(__file__).with_name('focus_browser.ps1').exists()
        assert (ASSETS/'index.html').exists() and (ASSETS/'desktop'/'bridge.js').exists()
        return
    store=SessionStore()
    if not store.acquire():
        try:
            info=json.loads(store.runtime.read_text(encoding='utf-8'))
            address=urlsplit(info['address'])
            if address.scheme!='http' or address.hostname!='127.0.0.1':
                raise ValueError('Invalid local launcher address')
            # Ask the already-running instance to select its report tab.
            request=Request(info['address']+'api/return',method='POST')
            with urlopen(request,timeout=3) as response:
                response.read()
        except Exception:
            root=tk.Tk();root.withdraw()
            messagebox.showinfo('FlashGuard is already running','Select the existing FlashGuard browser tab or launcher in your taskbar.',parent=root)
            root.destroy()
        return
    root = tk.Tk()
    root.withdraw()
    app = Desktop(root,store)
    server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server.app = app
    app.server = server
    app.address = f'http://127.0.0.1:{server.server_port}/{app.token}/'
    store.runtime.write_text(json.dumps({'address':app.address}),encoding='utf-8')
    if os.name!='nt':
        store.runtime.chmod(0o600)
    launcher = Launcher(root,app,app.open_browser)
    root.protocol('WM_DELETE_WINDOW',app.request_close)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    app.restore_session()
    root.iconify()
    root.after(100,app.dialogs)
    root.after(500,app.open_browser)
    try:
        root.mainloop()
    finally:
        app.analysis.pause()
        if app.thread:
            app.thread.join(10)
        warning=app.analysis.snapshot().get('checkpointWarning')
        if warning:
            messagebox.showwarning('Saved progress needs attention',warning,parent=root)
        server.shutdown()
        server.server_close()
        store.runtime.unlink(missing_ok=True)
        store.release()
        root.destroy()

if __name__ == '__main__':
    main()
