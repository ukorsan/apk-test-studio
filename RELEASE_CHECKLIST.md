# GitHub publishing checklist

Completed:
- [x] Independent source code, tests and original icons
- [x] Real AVD boot, APK installation, launch and screenshot tested
- [x] Windows EXE built and smoke-tested
- [x] README, privacy, security, release notes and Github Actions test workflow
- [x] Source and release packages verified, hashes calculated
- [x] No third-party Android SDK binaries or customer data in the repo

Remaining:
- [ ] Create a dedicated repository for APK Test Studio
- [ ] Choose the owner's source-code license (not yet chosen)
- [ ] Upload source files including hidden .github and .gitignore
- [ ] Confirm GitHub Actions unit tests pass
- [ ] Create a Draft Release, tag v0.1.0-beta.1, attach ZIP + SHA256SUMS.txt
- [ ] Mark as Pre-release until tested on another Windows PC
- [ ] Consider code signing before wide public distribution

Do not describe the controller as a self-contained Android emulator.
