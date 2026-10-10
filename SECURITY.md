# Security policy (beta)

APK Test Studio controls a local Android Emulator and does not scan APKs for malware. Do not use it to test malicious or unauthorized applications.

This beta restricts ADB calls to its own fixed emulator serial and checks the virtual device name. It does not ship Google SDK binaries and does not use a remote backend.

**Vulnerability reports:** Please do not disclose secret credentials, exploit details, client data, or proprietary APKs in public issues. Private vulnerability reporting may be enabled later by the repository maintainer.

Supported beta version: v0.1.0-beta.1.
