"""Compact launcher; analysis progress remains in the browser interface."""
import tkinter as tk


class Launcher:
    def __init__(self,root,app,open_browser):
        root.title('FlashGuard Desktop')
        root.geometry('340x82')
        root.resizable(False,False)
        root.configure(bg='#0b1422')
        self.return_button=tk.Button(root,text='Return to FlashGuard tab',command=open_browser,
            font=('Segoe UI',11,'bold'),bg='#82c7c0',fg='#0b1422',activebackground='#a4d7d1',
            relief='flat',borderwidth=0,padx=18,pady=12,cursor='hand2')
        self.return_button.pack(expand=True,padx=16,pady=12,fill='x')
