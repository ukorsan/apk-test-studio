# APK Test Studio

**A simple Windows controller for installing and testing Android APKs on the official Android Emulator.**

APK Test Studio lets developers select a local APK, install it with ADB, launch it in a private Android emulator, and use a clean white control sidebar for Home, Back, Recents, rotation and screenshots.

**Current version: v0.1.0-beta.1 — Windows x64 preview.** Validated on one Windows computer, not yet on a second machine.

> This application is **not** an emulator implementation, an official Google product or an Android Studio replacement. The Google Android Emulator is opened in its own window. No Google SDK components or Android system images are bundled.

## Features

| Tool | Function |
| --- | --- |
| APK picker | Inspect APK structure and package metadata when build-tools are available |
| Install | Install an explicitly selected APK in the tool's dedicated test device |
| Launch | Open the selected installed app |
| White control sidebar | Home, Back, Recent apps, Rotate, Screenshot, Shut down |
| Device manager | Create, start, check and stop a dedicated Android 15 AVD |
| Device safeguards | Only serial emulator-5586 and AVD name APKStudio_API35 are accepted |
| Port separation | Dedicated ADB port 5049 instead of default port 5037 |

## Prerequisites

- Windows 10/11 x64, virtualization support and at least 6 GB **free RAM** before launching the emulator.
- Official Android SDK components installed **separately** by the user: Emulator, Platform-Tools, Command-line Tools (latest), Android 15 / API 35 Google APIs x86_64 system image.
- JDK 17+ (tested with JDK 21). Android Build Tools are optional for reading APK package metadata.

Get official SDK installation instructions at https://developer.android.com/studio and review applicable third-party license terms.

## Install the Windows beta

1. Open **Releases** and download **APK_Test_Studio_Windows_v0.1.0-beta.1.zip**, not the GitHub-generated source archive.
2. Extract the ZIP and run APKTestStudio.exe.
3. Select the SDK installation folder in **Settings** (it contains platform-tools/adb.exe). Select the JDK folder if required.
4. Click **Create device**, then **Start device**.
5. Select **Check status** until Android reports Ready.
6. Click **Choose .apk**, select a legitimate APK, then click **Install on emulator**.
7. Click **Launch installed app**. The separate Google Emulator window displays the app.

The EXE is currently **unsigned**; Windows may warn about an unknown publisher. Verify release hashes, do not disable system protections, and only test trusted APKs. The controller does not itself download Android SDK packages.

## Privacy and isolation

The controller has no network backend, tracking or analytics. Selected APKs are processed locally; they are passed to the installed ADB tool only when you choose to install. Settings, screenshots and the new AVD reside in the Windows user profile at %LOCALAPPDATA%/APKTestStudio.

The underlying Android Emulator and apps installed inside it may communicate over networks independently. Emulation is **not** a guarantee of protection against malicious APKs. Only test files you have the right to install or inspect.

Only the dedicated AVD and ADB port are targeted. Existing virtual devices and attached phones are not intentionally modified.

See [Privacy](PRIVACY.md) and [Security](SECURITY.md).

## Develop from source

Python 3.11+ and Tkinter are required; no pip dependencies to run the source:

~~~powershell
python app.py
python -m unittest discover -s . -p "test_*.py" -v
~~~

Windows compilation instructions are in [BUILD.md](BUILD.md). CI runs automated tests in GitHub Actions.

## What was tested

On one Windows computer: independent Android 15 AVD creation, real debug APK validation, ADB installation, app launch, Android screenshot and shutdown of the private emulator. Seven Python unit tests passed. The unsigned packaged Windows EXE launched successfully.

Not yet verified: another clean Windows computer, alternate Android APIs, malicious-APK containment, code signing, or production support.

## License status

The owner has **not yet selected a source-code license**. Publicly visible source code does not automatically authorize commercial reuse, modification or redistribution. This repository should not be marketed as "open source" until the owner explicitly selects a license.

See [release notes](RELEASE_NOTES.md) and the [release checklist](RELEASE_CHECKLIST.md).
