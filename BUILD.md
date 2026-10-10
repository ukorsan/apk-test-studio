# Windows executable build

Source runtime: Python 3.11+ with Tkinter. The tested EXE was compiled with Python 3.14.7 and PyInstaller 6.22.3.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check pyinstaller==6.22.3
.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm --onefile --windowed --name APKTestStudio --icon assets\logo.ico app.py
~~~

The result is dist/APKTestStudio.exe. Upload executable releases separately under GitHub Releases, rather than committing EXE files into source history.

Never bundle Google Android Emulator, system images, Android SDK components or JDK in the release. Users configure their own installations.

Before recommending public use: verify a new build, check hashes, test on a second Windows computer, and consider signing the EXE.
