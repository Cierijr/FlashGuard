"""Desktop status window and optional, non-flashing Pong break."""
from dataclasses import dataclass
import time
import tkinter as tk
from tkinter import ttk

BG='#0b1422'
CARD='#142235'
TEXT='#e8eef4'
MUTED='#a6b7c8'
TEAL='#82c7c0'

@dataclass
class Pong:
    width: int = 600
    height: int = 190
    x: float = 300
    y: float = 95
    vx: float = 150
    vy: float = 65
    paddle: float = 95
    opponent: float = 95
    player_score: int = 0
    opponent_score: int = 0
    playing: bool = False

    def move(self,y):
        self.paddle=max(24,min(self.height-24,y))

    def serve(self,direction):
        self.x,self.y=self.width/2,self.height/2
        self.vx,self.vy=150*direction,65

    def step(self,dt):
        if not self.playing:
            return
        dt=max(0,min(.05,dt))
        self.opponent+=max(-100*dt,min(100*dt,self.y-self.opponent))
        self.opponent=max(24,min(self.height-24,self.opponent))
        self.x+=self.vx*dt
        self.y+=self.vy*dt
        if self.y<7:
            self.y=7;self.vy=abs(self.vy)
        elif self.y>self.height-7:
            self.y=self.height-7;self.vy=-abs(self.vy)
        if self.vx<0 and 16<=self.x<=30 and abs(self.y-self.paddle)<=30:
            self.x=30;self.vx=abs(self.vx);self.vy=(self.y-self.paddle)*3
        elif self.vx>0 and self.width-30<=self.x<=self.width-16 and abs(self.y-self.opponent)<=30:
            self.x=self.width-30;self.vx=-abs(self.vx);self.vy=(self.y-self.opponent)*3
        if self.x<0:
            self.opponent_score+=1;self.serve(1)
        elif self.x>self.width:
            self.player_score+=1;self.serve(-1)


def duration(seconds):
    seconds=max(0,int(seconds))
    return f'{seconds//60}:{seconds%60:02d}'

class Launcher:
    def __init__(self,root,app,open_browser):
        self.root,self.app=root,app
        self.pong=Pong()
        self.last_tick=time.monotonic()
        self.last_status=None
        root.title('FlashGuard Desktop — local analysis')
        root.geometry(f'720x{min(820,max(560,root.winfo_screenheight()-100))}')
        root.minsize(680,520)
        root.configure(bg=BG)
        root.option_add('*Font','{Segoe UI} 10')
        style=ttk.Style(root)
        style.theme_use('clam')
        style.configure('Flash.Horizontal.TProgressbar',troughcolor=BG,background=TEAL,bordercolor=BG,lightcolor=TEAL,darkcolor=TEAL)
        scroll=tk.Canvas(root,bg=BG,highlightthickness=0)
        scrollbar=ttk.Scrollbar(root,orient='vertical',command=scroll.yview)
        scrollbar.pack(side='right',fill='y');scroll.pack(side='left',fill='both',expand=True)
        scroll.configure(yscrollcommand=scrollbar.set)
        body=tk.Frame(scroll,bg=BG,padx=28,pady=22)
        content=scroll.create_window((0,0),window=body,anchor='nw')
        body.bind('<Configure>',lambda event:scroll.configure(scrollregion=scroll.bbox('all')))
        scroll.bind('<Configure>',lambda event:scroll.itemconfigure(content,width=event.width))
        root.bind('<MouseWheel>',lambda event:scroll.yview_scroll(-int(event.delta/120),'units'))
        header=tk.Frame(body,bg=BG);header.pack(fill='x')
        tk.Label(header,text='FlashGuard',bg=BG,fg=TEXT,font=('Segoe UI',25,'bold')).pack(side='left')
        tk.Label(header,text='DESKTOP',bg=BG,fg=TEAL,font=('Segoe UI',10,'bold')).pack(side='left',padx=12,pady=(12,0))
        tk.Label(body,text='Your video stays on your computer.',bg=BG,fg=MUTED).pack(anchor='w',pady=(0,18))
        card=tk.Frame(body,bg=CARD,padx=20,pady=16);card.pack(fill='x')
        self.status=tk.Label(card,text='Ready when you are',font=('Segoe UI',15,'bold'),bg=CARD,fg=TEXT)
        self.status.pack(anchor='w')
        self.filename=tk.Label(card,text='Choose a video in the browser to begin.',bg=CARD,fg=MUTED,wraplength=570,anchor='w',justify='left')
        self.filename.pack(anchor='w',pady=(6,12))
        self.progress=ttk.Progressbar(card,maximum=100,style='Flash.Horizontal.TProgressbar');self.progress.pack(fill='x')
        self.detail=tk.Label(card,text='Local decoder connected',bg=CARD,fg=TEAL,anchor='w',wraplength=570)
        self.detail.pack(anchor='w',pady=(9,0))
        tk.Label(body,text='Keep this window open while you use FlashGuard.',bg=BG,fg=TEXT,font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(18,3))
        tk.Label(body,text='You can minimize it. Closing it disconnects the browser interface.',bg=BG,fg=MUTED).pack(anchor='w')
        actions=tk.Frame(body,bg=BG);actions.pack(fill='x',pady=(14,18))
        self.button(actions,'Open FlashGuard in browser',open_browser,primary=True).pack(side='left')
        self.button(actions,'Minimize',root.iconify).pack(side='left',padx=10)
        game=tk.Frame(body,bg=CARD,padx=16,pady=14);game.pack(fill='x')
        row=tk.Frame(game,bg=CARD);row.pack(fill='x')
        tk.Label(row,text='A little break · Pong',bg=CARD,fg=TEXT,font=('Segoe UI',12,'bold')).pack(side='left')
        self.play_button=self.button(row,'Play Pong',self.toggle);self.play_button.pack(side='right')
        self.game_help=tk.Label(game,text='Optional · starts paused · no sound or flashing effects',bg=CARD,fg=MUTED,anchor='w')
        self.game_help.pack(anchor='w',pady=(4,8))
        self.canvas=tk.Canvas(game,width=600,height=190,bg=BG,highlightthickness=1,highlightbackground='#294052',takefocus=True)
        self.canvas.pack()
        self.canvas.create_line(300,12,300,178,fill='#243749',dash=(4,8))
        self.ball=self.canvas.create_oval(0,0,0,0,fill='#a4c2c8',outline='')
        self.left=self.canvas.create_rectangle(18,0,26,0,fill=TEAL,outline='')
        self.right=self.canvas.create_rectangle(574,0,582,0,fill='#8b9cac',outline='')
        self.score=self.canvas.create_text(300,20,text='0 : 0',fill=MUTED,font=('Segoe UI',12))
        self.overlay=self.canvas.create_text(300,100,text='Play when you feel like a break',fill=MUTED,font=('Segoe UI',12))
        self.canvas.bind('<Motion>',lambda event:self.pong.move(event.y) if self.pong.playing else None)
        self.canvas.bind('<Up>',lambda event:self.key_move(-20))
        self.canvas.bind('<Down>',lambda event:self.key_move(20))
        self.canvas.bind('<space>',lambda event:self.toggle())
        self.canvas.bind('<FocusOut>',lambda event:root.after_idle(self.check_focus))
        tk.Label(body,text='Move your mouse over the court, or use ↑ / ↓. Space pauses.\nThe game pauses when you leave it or analysis finishes.',bg=BG,fg=MUTED,justify='left').pack(anchor='w',pady=(10,0))
        self.draw()
        self.root.after(250,self.refresh)
        self.root.after(33,self.tick)

    @staticmethod
    def button(parent,text,command,primary=False):
        return tk.Button(parent,text=text,command=command,bg=TEAL if primary else '#24394d',fg=BG if primary else TEXT,
            activebackground='#a4d7d1' if primary else '#324c62',activeforeground=BG if primary else TEXT,
            relief='flat',borderwidth=0,padx=13,pady=9,cursor='hand2')

    def check_focus(self):
        if self.root.focus_get() not in (self.canvas,self.play_button):
            self.pause('Paused — press Play Pong to continue')

    def key_move(self,amount):
        if self.pong.playing:
            self.pong.move(self.pong.paddle+amount)
        return 'break'

    def pause(self,message='Paused'):
        self.pong.playing=False
        self.play_button.configure(text='Play Pong')
        self.canvas.itemconfigure(self.overlay,text=message,state='normal')

    def toggle(self):
        if self.pong.playing:
            self.pause('Paused — press Play Pong to continue')
        else:
            self.pong.playing=True
            self.last_tick=time.monotonic()
            self.canvas.focus_set()
            self.play_button.configure(text='Pause Pong')
            self.canvas.itemconfigure(self.overlay,state='hidden')

    def draw(self):
        p=self.pong
        self.canvas.coords(self.ball,p.x-6,p.y-6,p.x+6,p.y+6)
        self.canvas.coords(self.left,18,p.paddle-24,26,p.paddle+24)
        self.canvas.coords(self.right,574,p.opponent-24,582,p.opponent+24)
        self.canvas.itemconfigure(self.score,text=f'{p.player_score} : {p.opponent_score}')

    def tick(self):
        now=time.monotonic()
        if self.pong.playing:
            if self.root.state()=='iconic':
                self.pause('Paused while minimized')
            else:
                self.pong.step(now-self.last_tick)
                self.draw()
        self.last_tick=now
        self.root.after(33 if self.pong.playing else 250,self.tick)

    def refresh(self):
        state=self.app.analysis.snapshot()
        status=state.get('status','idle')
        title={'idle':'Ready when you are','analyzing':'Analyzing your video','complete':'Your report is ready','cancelled':'Analysis stopped','error':'Analysis needs attention'}.get(status,'FlashGuard is running')
        self.status.configure(text=title)
        name=self.app.filename.name if self.app.filename else 'Choose a video in the browser to begin.'
        self.filename.configure(text=name)
        self.progress['value']=state.get('progress',0)
        if status=='analyzing':
            remaining=duration(state['remainingSeconds']) if 'remainingSeconds' in state else 'estimating…'
            detail=f"{state.get('progress',0):.0f}% · {state.get('frames',0):,} frames · estimated remaining {remaining}"
        elif status=='complete':
            detail='Return to the browser to review your results. Keep this launcher open.'
        elif status in ('error','cancelled'):
            detail=state.get('message','Choose another video in the browser.')
        else:
            detail='Local decoder connected · nothing plays automatically'
        self.detail.configure(text=detail)
        if status=='complete' and self.last_status!='complete':
            self.pause('Analysis complete — your report is ready in the browser')
        self.last_status=status
        self.root.after(250,self.refresh)
