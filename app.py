"""APK Test Studio — GUI (stdlib Tkinter, no third-party runtime dependencies).

A standalone launcher/controller for an Android SDK installed by the user.
Google Android Emulator opens in its own native window; this interface supplies
a separate white control rail and a simple file picker for Android APKs.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
import sys, threading
import tkinter as tk
from tkinter import filedialog, messagebox
from core import Bridge, APK, inspect_apk, load_settings, save_settings, user_root

BG="#F2F5F7"
WHITE="#FFFFFF"
INK="#16242E"
SUB="#637583"
FAINT="#DDE6EB"
TEAL="#148D77"
LIGHT="#DDF6EF"
DARK="#0F2733"
RED="#B53E49"
FONT="Segoe UI"

def label(parent,text,size=11,color=INK,bold=False,bg=BG,**kwargs):
    return tk.Label(parent,text=text,bg=bg,fg=color,font=(FONT,size,"bold" if bold else "normal"),**kwargs)

class TestStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("APK Test Studio  •  Android APK Testing")
        self.geometry("1150x760")
        self.minsize(980,720)
        self.configure(bg=BG)
        self.queue=Queue()
        self.busy=False
        self.current:APK|None=None
        self.config_data=load_settings()
        self.bridge=Bridge(self.config_data.get("sdk_root",""),self.config_data.get("java_home",""))
        self.status_var=tk.StringVar(value="Not connected — start a private test device to begin")
        self.apk_title=tk.StringVar(value="No APK selected yet")
        self.apk_meta=tk.StringVar(value="Choose an Android APK to inspect it before installation.")
        self.sdk_title=tk.StringVar(value="Android SDK not configured")
        self.last_msg=tk.StringVar(value="Ready to configure your Android testing workspace.")
        self.controls=[]
        self._build()
        self._sdk_label()
        self.bind("<Control-o>",lambda e:self.pick_apk())
        self.after(120,self._poll)
        self.protocol("WM_DELETE_WINDOW",self._close)

    def _build(self):
        # Left white side rail; visually distinct from Google's own emulator toolbar.
        rail=tk.Frame(self,bg=WHITE,width=176,highlightbackground=FAINT,highlightthickness=1)
        rail.pack(side="left",fill="y")
        rail.pack_propagate(False)
        tk.Label(rail,text="◈",bg=WHITE,fg=TEAL,font=(FONT,27,"bold")).pack(anchor="w",padx=23,pady=(24,3))
        label(rail,"APK TEST",14,INK,True,WHITE).pack(anchor="w",padx=22)
        label(rail,"STUDIO",14,TEAL,True,WHITE).pack(anchor="w",padx=22)
        label(rail,"DEVELOPER TOOL",8,SUB,True,WHITE).pack(anchor="w",padx=22,pady=(8,35))
        label(rail,"ANDROID CONTROLS",8,SUB,True,WHITE).pack(anchor="w",padx=22,pady=(0,8))
        self.rail_btn(rail,"⌂", "Home",lambda:self.action("Home",lambda:self.bridge.key(3)))
        self.rail_btn(rail,"←", "Back",lambda:self.action("Back",lambda:self.bridge.key(4)))
        self.rail_btn(rail,"▢", "Recent apps",lambda:self.action("Recents",lambda:self.bridge.key(187)))
        self.rail_btn(rail,"↻", "Rotate",lambda:self.action("Rotate",self.bridge.rotate))
        self.rail_btn(rail,"▣", "Screenshot",self.make_screenshot)
        tk.Frame(rail,bg=FAINT,height=1).pack(fill="x",padx=20,pady=22)
        self.rail_btn(rail,"＋", "Install APK",self.pick_apk,accent=True)
        self.rail_btn(rail,"⚙", "Settings",self.settings_dialog)
        self.rail_btn(rail,"⏻", "Shut down",lambda:self.action("Shutdown",self.bridge.stop))
        tk.Frame(rail,bg=WHITE).pack(expand=True)
        label(rail,"Private emulator",9,SUB,False,WHITE).pack(anchor="w",padx=22,pady=(0,4))
        label(rail,"Private AVD only",8,TEAL,True,WHITE).pack(anchor="w",padx=22,pady=(0,25))
        # Main work area.
        main=tk.Frame(self,bg=BG)
        main.pack(side="left",fill="both",expand=True)
        top=tk.Frame(main,bg=BG)
        top.pack(fill="x",padx=36,pady=(29,0))
        label(top,"Android testing, simplified.",25,INK,True).pack(anchor="w")
        label(top,"Install, launch and inspect your own APKs in an isolated virtual device.",11,SUB).pack(anchor="w",pady=(5,0))
        line=tk.Frame(main,bg=FAINT,height=1)
        line.pack(fill="x",padx=35,pady=(24,20))
        self.panes=tk.Frame(main,bg=BG)
        self.panes.pack(fill="both",expand=True,padx=35)
        left=tk.Frame(self.panes,bg=BG)
        left.pack(side="left",fill="both",expand=True,padx=(0,11))
        right=tk.Frame(self.panes,bg=BG,width=290)
        right.pack(side="left",fill="y",padx=(11,0))
        right.pack_propagate(False)

        device=self.card(left,padx=24,pady=20)
        device.pack(fill="both",expand=True)
        label(device,"YOUR TEST DEVICE",9,TEAL,True,WHITE).pack(anchor="w")
        label(device,"Android 15 · API 35",20,INK,True,WHITE).pack(anchor="w",pady=(11,2))
        status=label(device,"",10,SUB,bg=WHITE,anchor="w",wraplength=420,justify="left")
        status.pack(anchor="w",fill="x",pady=(0,12))
        status.configure(textvariable=self.status_var)
        mock=tk.Canvas(device,height=214,background="#102C36",highlightthickness=0)
        mock.pack(fill="both",expand=True,pady=(8,18))
        self.visual=mock
        mock.bind("<Configure>",lambda e:self._draw_device(e.width,e.height))
        buttons=tk.Frame(device,bg=WHITE)
        buttons.pack(fill="x")
        self.add_button(buttons,"Start device",self.start_device,primary=True).pack(side="left",padx=(0,8))
        self.add_button(buttons,"Create device",self.create_device).pack(side="left",padx=(0,8))
        self.add_button(buttons,"Check status",self.check_status).pack(side="left")

        appcard=self.card(right,padx=20,pady=18)
        appcard.pack(fill="x",pady=(0,18))
        label(appcard,"01  IMPORT APPLICATION",9,TEAL,True,WHITE).pack(anchor="w")
        label(appcard,"Your APK",20,INK,True,WHITE).pack(anchor="w",pady=(9,4))
        label(appcard,"Choose a file. Nothing installs until you click Install.",10,SUB,bg=WHITE,justify="left",wraplength=245).pack(anchor="w",pady=(0,15))
        filebox=tk.Frame(appcard,bg="#F2F6F7",highlightthickness=1,highlightbackground=FAINT,padx=12,pady=12)
        filebox.pack(fill="x")
        label(filebox,"▤",26,TEAL,bg="#F2F6F7").pack(anchor="w")
        label(filebox,"",11,INK,True,bg="#F2F6F7",wraplength=220,justify="left",textvariable=self.apk_title).pack(anchor="w")
        label(filebox,"",9,SUB,bg="#F2F6F7",wraplength=220,justify="left",textvariable=self.apk_meta).pack(anchor="w",pady=(7,0))
        self.add_button(appcard,"Choose .apk  ↗",self.pick_apk).pack(fill="x",pady=(16,6))
        self.install_btn=self.add_button(appcard,"Install on emulator",self.install_apk,primary=True)
        self.install_btn.pack(fill="x",pady=(4,4))
        self.run_btn=self.add_button(appcard,"Launch installed app",self.launch_apk)
        self.run_btn.pack(fill="x",pady=(4,3))

        # SDK settings are available from the permanent white side menu.
        # The private AVD can be created directly from the main device card.

        bottom=tk.Frame(main,bg=WHITE,highlightthickness=1,highlightbackground=FAINT)
        bottom.pack(fill="x",padx=35,pady=(19,24))
        line1=tk.Frame(bottom,bg=WHITE)
        line1.pack(fill="x",padx=16,pady=(10,4))
        label(line1,"ACTIVITY",9,TEAL,True,WHITE).pack(side="left")
        self.log=tk.Text(bottom,height=3,wrap="word",bg=WHITE,fg=SUB,font=("Consolas",9),bd=0,highlightthickness=0,state="disabled")
        self.log.pack(fill="x",padx=16,pady=(0,12))
        self.log_message("Welcome. Select the Android SDK in Settings to get started.")

    def card(self,parent,padx=20,pady=20):
        c=tk.Frame(parent,bg=WHITE,highlightbackground=FAINT,highlightthickness=1,padx=padx,pady=pady)
        return c

    def rail_btn(self,parent,icon,name,command,accent=False):
        b=tk.Button(parent,text=f"  {icon}    {name}",command=command,
                    bg=LIGHT if accent else WHITE,fg=TEAL if accent else INK,
                    activebackground=LIGHT,activeforeground=TEAL,relief="flat",
                    anchor="w",font=(FONT,10,"bold" if accent else "normal"),
                    cursor="hand2",bd=0,pady=13)
        b.pack(fill="x",padx=12,pady=2)
        self.controls.append(b)
        return b

    def add_button(self,parent,text,command,primary=False):
        b=tk.Button(parent,text=text,command=command,relief="flat",bd=0,
                 bg=TEAL if primary else "#E9F2F1",fg=WHITE if primary else DARK,
                 activebackground="#08715F" if primary else LIGHT,
                 activeforeground=WHITE if primary else DARK,
                 cursor="hand2",font=(FONT,10,"bold"),padx=15,pady=12)
        self.controls.append(b)
        return b

    def _draw_device(self,w,h):
        if w<70 or h<70:return
        c=self.visual
        c.delete("all")
        x=w/2;y=h/2
        c.create_oval(x-90,y-80,x+90,y+100,fill="#143E47",outline="")
        c.create_rectangle(x-46,y-75,x+46,y+87,fill="#081A22",outline="#4F8890",width=3)
        c.create_rectangle(x-37,y-63,x+37,y+69,fill="#174B54",outline="")
        c.create_oval(x-13,y-13,x+13,y+13,fill=TEAL,outline="")
        c.create_text(x,y+41,text="APK",fill="#D8F5EA",font=(FONT,13,"bold"))
        c.create_text(x,y+115,text="ISOLATED ANDROID ENVIRONMENT",fill="#A2C4C8",font=(FONT,8,"bold"))

    def _poll(self):
        try:
            while True:
                kind,arg,callback=self.queue.get_nowait()
                if kind=="success":
                    self.log_message(str(arg))
                    if callback:callback(arg)
                else:
                    self.log_message("ERROR: "+str(arg))
                    messagebox.showerror("APK Test Studio",str(arg))
                self.busy=False
                self._lock_ui(False)
        except Empty:pass
        self.after(120,self._poll)

    def _lock_ui(self,locked):
        for b in self.controls:
            try:b.configure(state="disabled" if locked else "normal")
            except tk.TclError:pass

    def action(self,description,fn,callback=None):
        if self.busy:return
        self.busy=True;self._lock_ui(True)
        self.log_message("Working: "+description+"...")
        def work():
            try:self.queue.put(("success",fn(),callback))
            except Exception as exc:self.queue.put(("error",str(exc),None))
        threading.Thread(target=work,daemon=True).start()

    def log_message(self,message):
        self.log.configure(state="normal")
        self.log.insert("end",f"[{datetime.now():%H:%M:%S}] {message}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _sdk_label(self):
        p=self.config_data.get("sdk_root","")
        self.sdk_title.set("SDK: "+(Path(p).name+" (configured)" if p else "Not configured")+
                           "\nPrivate emulator · dedicated ADB port 5049")

    def settings_dialog(self):
        popup=tk.Toplevel(self)
        popup.title("Settings · APK Test Studio")
        popup.geometry("650x350")
        popup.minsize(560,340)
        popup.transient(self);popup.grab_set()
        popup.configure(bg=BG)
        label(popup,"Android SDK configuration",20,INK,True).pack(anchor="w",padx=28,pady=(25,8))
        label(popup,"Select an officially installed Android SDK. Nothing is copied or modified.",10,SUB).pack(anchor="w",padx=28)
        values={}
        for key,title in (("sdk_root","Android SDK folder"),("java_home","JDK 17+ folder (optional)")):
            frame=tk.Frame(popup,bg=BG);frame.pack(fill="x",padx=28,pady=(15,0))
            label(frame,title,10,INK,True).pack(anchor="w")
            line=tk.Frame(frame,bg=BG);line.pack(fill="x",pady=(5,0))
            var=tk.StringVar(value=self.config_data.get(key,""))
            ent=tk.Entry(line,textvariable=var,font=(FONT,10),bg=WHITE,fg=INK,relief="flat",highlightthickness=1,highlightbackground=FAINT)
            ent.pack(side="left",fill="x",expand=True,ipady=9)
            tk.Button(line,text="Browse",command=lambda v=var:v.set(filedialog.askdirectory(parent=popup) or v.get()),
                      bg=WHITE,fg=TEAL,bd=0,cursor="hand2",font=(FONT,9,"bold"),padx=13).pack(side="left",padx=(5,0),ipady=9)
            values[key]=var
        def commit():
            cfg={k:v.get().strip() for k,v in values.items()}
            if cfg["sdk_root"] and not (Path(cfg["sdk_root"])/"platform-tools"/"adb.exe").is_file():
                messagebox.showerror("Invalid SDK","Select a folder containing platform-tools/adb.exe",parent=popup)
                return
            if cfg["java_home"] and not (Path(cfg["java_home"])/"bin"/"java.exe").is_file():
                messagebox.showerror("Invalid JDK","Select the JDK installation root folder.",parent=popup)
                return
            save_settings(cfg)
            self.config_data=cfg
            self.bridge=Bridge(cfg["sdk_root"],cfg["java_home"])
            self._sdk_label()
            self.log_message("SDK settings saved in the APK Test Studio profile.")
            popup.destroy()
        self.add_button(popup,"Save configuration",commit,primary=True).pack(anchor="e",padx=28,pady=22)

    def pick_apk(self):
        path=filedialog.askopenfilename(parent=self,title="Choose APK to test",filetypes=[("Android package","*.apk")])
        if not path:return
        def inspect():
            return inspect_apk(path,self.bridge.aapt if self.bridge.adb.exists() else None,self.bridge.env())
        def on_apk(meta):
            self.current=meta
            self.apk_title.set(meta.path.name)
            self.apk_meta.set(f"{meta.size/(1024**2):.1f} MB  ·  {meta.package or 'Package not detected'}")
        self.action("Inspect APK",inspect,on_apk)

    def install_apk(self):
        if not self.current:
            messagebox.showinfo("Choose APK","Choose an APK first.")
            return
        self.action("Install APK",lambda:self.bridge.install(self.current))

    def launch_apk(self):
        if not self.current:
            messagebox.showinfo("Choose APK","Choose an APK first.")
            return
        self.action("Launch APK",lambda:self.bridge.launch(self.current))

    def create_device(self):
        self.action("Create private Android AVD",self.bridge.create_avd)

    def start_device(self):
        self.action("Start emulator",self.bridge.start,lambda _:self.after(4000,self.check_status))

    def check_status(self):
        self.action("Check private emulator",self.bridge.status,
                    lambda status:self.status_var.set(status))

    def make_screenshot(self):
        self.action("Capture private device screenshot",self.bridge.screenshot,
                    lambda p:self.log_message("Saved screenshot in APK Test Studio data folder."))

    def _close(self):
        # Closing the controller does not kill running emulators or any other user process.
        self.destroy()

if __name__=="__main__":
    app=TestStudio()
    if "--smoke" in sys.argv:
        def check():
            try:
                app.update()
                from PIL import ImageGrab
                x,y=app.winfo_rootx(),app.winfo_rooty()
                w,h=app.winfo_width(),app.winfo_height()
                ImageGrab.grab(bbox=(x,y,x+w,y+h)).save(Path(__file__).parent/"preview.png")
            finally:app.destroy()
        app.after(1800,check)
    app.mainloop()
