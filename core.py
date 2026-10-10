"""APK Test Studio core. Targets only its own dedicated Android AVD/ADB server.

No modification or redistribution of Android SDK and other project components.
"""
from __future__ import annotations
import ctypes
from dataclasses import dataclass
from pathlib import Path
import json, os, re, socket, subprocess, zipfile

NAME="APKStudio_API35"
PORT=5586
SERIAL=f"emulator-{PORT}"
ADB_PORT="5049"
MIN_RAM=6.0
IMAGE="system-images;android-35;google_apis;x86_64"
MAX_SIZE=1024**3

def user_root():
    return Path(os.environ.get("APK_TEST_STUDIO_DATA",str(Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"APKTestStudio"))).resolve()

def settings(root=None):
    p=(root or user_root())/"settings.json"
    try: return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:return {"sdk_root":"","java_home":""}

def load_settings(root=None):
    return settings(root)

def save_settings(values,root=None):
    p=root or user_root()
    p.mkdir(parents=True,exist_ok=True)
    (p/"settings.json").write_text(json.dumps({k:str(values.get(k,"")) for k in ("sdk_root","java_home")},indent=2),encoding="utf-8")

def free_ram_gb():
    if os.name!="nt":return 0.0
    class M(ctypes.Structure):
        _fields_=[("dwLength",ctypes.c_ulong),("dwMemoryLoad",ctypes.c_ulong)]+[(x,ctypes.c_ulonglong) for x in ("ullTotalPhys","ullAvailPhys","ullTotalPageFile","ullAvailPageFile","ullTotalVirtual","ullAvailVirtual","ullAvailExtendedVirtual")]
    m=M();m.dwLength=ctypes.sizeof(M)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):raise OSError("Could not check RAM")
    return m.ullAvailPhys/(1024**3)

@dataclass(frozen=True)
class APK:
    path:Path
    size:int
    package:str=""
    label:str=""

def inspect_apk(value,aapt=None,env=None):
    p=Path(value).resolve(strict=True)
    if not p.is_file() or p.suffix.lower()!=".apk":raise ValueError("Choose an .apk file.")
    n=p.stat().st_size
    if n<1 or n>MAX_SIZE:raise ValueError("APK is empty or larger than 1 GB.")
    if not zipfile.is_zipfile(p):raise ValueError("Not a valid APK (ZIP signature missing).")
    with zipfile.ZipFile(p) as z:
        if "AndroidManifest.xml" not in z.namelist():raise ValueError("Invalid APK: AndroidManifest.xml not found.")
    pkg=label=""
    if aapt and aapt.is_file():
        r=subprocess.run([str(aapt),"dump","badging",str(p)],capture_output=True,text=True,errors="replace",timeout=20,env=env,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if r.returncode==0:
            m=re.search(r"^package: name='([^']+)'",r.stdout,re.M);pkg=m.group(1) if m else ""
            m=re.search(r"^application-label:'([^']*)'",r.stdout,re.M);label=m.group(1) if m else ""
    return APK(p,n,pkg,label)

class Bridge:
    def __init__(self,sdk_root="",java_home="",root=None):
        self.sdk=Path(sdk_root).expanduser().resolve() if sdk_root else Path("UNCONFIGURED")
        self.java_home=java_home
        self.root=root or user_root()
        self.avd_home=self.root/"avds"
        self.avd=self.avd_home/(NAME+".avd")
    def env(self):
        env=os.environ.copy()
        env.update({"ANDROID_HOME":str(self.sdk),"ANDROID_SDK_ROOT":str(self.sdk),
                    "ANDROID_AVD_HOME":str(self.avd_home),"ADB_SERVER_PORT":ADB_PORT})
        if self.java_home:
            env["JAVA_HOME"]=self.java_home
            env["PATH"]=str(Path(self.java_home)/"bin")+os.pathsep+env.get("PATH","")
        return env
    @property
    def adb(self):return self.sdk/"platform-tools"/"adb.exe"
    @property
    def emulator(self):return self.sdk/"emulator"/"emulator.exe"
    @property
    def avdmanager(self):return self.sdk/"cmdline-tools"/"latest"/"bin"/"avdmanager.bat"
    @property
    def aapt(self):
        for v in ("35.0.0","36.0.0","37.0.0","34.0.0"):
            p=self.sdk/"build-tools"/v/"aapt.exe"
            if p.is_file():return p
        return None
    def validate(self,emulator=False):
        if not self.adb.is_file():raise FileNotFoundError("Select an Android SDK folder containing platform-tools/adb.exe.")
        if emulator:
            if not self.emulator.is_file() or not self.avdmanager.is_file():raise FileNotFoundError("Android Emulator or Command-line Tools missing.")
            if not (self.sdk/"system-images"/"android-35"/"google_apis"/"x86_64").is_dir():raise FileNotFoundError("Install Android 15 / Google APIs / x86_64 system image via SDK Manager.")
    def run(self,args,timeout=25,input=None):
        return subprocess.run([str(x) for x in args],input=input,env=self.env(),capture_output=True,text=True,errors="replace",timeout=timeout,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    def owned(self):
        if not self.adb.is_file():return False
        try:
            devices=self.run([self.adb,"devices"],8)
            if not re.search(r"^"+re.escape(SERIAL)+r"\s+device\b",devices.stdout,re.M):return False
            name=self.run([self.adb,"-s",SERIAL,"emu","avd","name"],8)
            return name.returncode==0 and NAME in name.stdout.splitlines()
        except (OSError,subprocess.TimeoutExpired):return False
    def command(self,*args,timeout=25):
        self.validate()
        if not self.owned():raise RuntimeError("Private emulator offline. Other devices will not be touched.")
        return self.run([self.adb,"-s",SERIAL,*args],timeout)
    def status(self):
        if not self.adb.is_file():return "SDK not configured"
        if not self.owned():return "Offline — private emulator not connected"
        b=self.command("shell","getprop","sys.boot_completed",timeout=12)
        return "Ready — Android online" if b.stdout.strip()=="1" else "Booting — please wait"
    def require_ready(self):
        if not self.owned():
            raise RuntimeError("Private Android test device is offline.")
        response=self.command("shell","getprop","sys.boot_completed",timeout=12)
        if response.stdout.strip()!="1":
            raise RuntimeError("Android is still starting. Wait until Check status shows Ready, then try again.")

    def avd_exists(self):
        return self.avd.is_dir() and (self.avd/"config.ini").is_file()
    def create_avd(self):
        self.validate(True)
        if self.avd_exists():return "Private Android test device already exists."
        self.avd_home.mkdir(parents=True,exist_ok=True)
        if (self.avd_home/(NAME+".ini")).exists():raise RuntimeError("Incomplete private AVD detected. Manual review required.")
        r=self.run([self.avdmanager,"create","avd","-n",NAME,"-k",IMAGE,"-p",self.avd],75,input="no\n")
        if r.returncode or not self.avd_exists():raise RuntimeError("Cannot create private test device: "+(r.stderr or r.stdout)[-750:])
        with (self.avd/"config.ini").open("a",encoding="utf-8") as cfg:cfg.write("\nhw.ramSize=2048\nvm.heapSize=256\n")
        return "Private AVD created outside other projects."
    def start(self):
        self.validate(True)
        if self.owned():return "Private emulator already running."
        for p in (PORT,PORT+1):
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1",p))==0:raise RuntimeError("Dedicated emulator port occupied. Refusing to start.")
        available=free_ram_gb()
        if available<MIN_RAM:raise RuntimeError(f"Only {available:.1f} GB RAM free; {MIN_RAM:g} GB required.")
        if not self.avd_exists():raise RuntimeError("Create private Android device first.")
        subprocess.Popen([str(self.emulator),"-avd",NAME,"-port",str(PORT),"-memory","2048","-gpu","auto","-no-snapshot-save"],
            cwd=self.sdk/"emulator",env=self.env(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        return "Starting isolated Android emulator. Boot may take a minute."
    def install(self,apk):
        self.require_ready()
        if not apk.path.is_file():raise FileNotFoundError("APK no longer exists.")
        r=self.command("install","-r",str(apk.path),timeout=180)
        if r.returncode or "Success" not in r.stdout:raise RuntimeError("Install failed: "+(r.stdout+r.stderr)[-700:])
        return "Installed: "+(apk.package or apk.path.name)
    def key(self,value):
        if value not in (3,4,187,24,25):raise ValueError("Unsupported Android key")
        self.require_ready()
        r=self.command("shell","input","keyevent",str(value),timeout=12)
        if r.returncode:raise RuntimeError(r.stderr[-400:])
        return "Command sent to private emulator."
    def rotate(self):
        self.require_ready()
        self.command("shell","settings","put","system","accelerometer_rotation","0",timeout=12)
        r=self.command("shell","settings","get","system","user_rotation",timeout=12)
        self.command("shell","settings","put","system","user_rotation","0" if r.stdout.strip()=="1" else "1",timeout=12)
        return "Screen orientation updated."
    def screenshot(self):
        self.require_ready()
        from datetime import datetime
        p=self.root/"screenshots";p.mkdir(parents=True,exist_ok=True)
        output=p/("test-"+datetime.now().strftime("%Y%m%d-%H%M%S")+".png")
        r=subprocess.run([str(self.adb),"-s",SERIAL,"exec-out","screencap","-p"],env=self.env(),capture_output=True,timeout=35,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if r.returncode or not r.stdout.startswith(b"\x89PNG\r\n\x1a\n"):raise RuntimeError("Could not capture Android screenshot.")
        output.write_bytes(r.stdout);return output
    def stop(self):
        r=self.command("emu","kill",timeout=15)
        if r.returncode:raise RuntimeError("Private emulator shutdown failed.")
        # Shut down ONLY our dedicated ADB server port; never touch default 5037.
        self.run([self.adb,"-P",ADB_PORT,"kill-server"],timeout=12)
        return "Private emulator and its dedicated ADB server stopped."
    def launch(self,apk):
        self.require_ready()
        if not apk.package:raise ValueError("APK package could not be identified.")
        r=self.command("shell","monkey","-p",apk.package,"-c","android.intent.category.LAUNCHER","1",timeout=15)
        if r.returncode or "Events injected: 1" not in r.stdout:raise RuntimeError("Could not launch APK.")
        return "Launched "+apk.package
