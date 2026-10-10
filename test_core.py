"""Safety and behavior checks for APK Test Studio. Does not start an emulator."""
import tempfile, pathlib, sys, unittest, zipfile
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from core import (Bridge,APK,inspect_apk,load_settings,save_settings,
                  PORT,SERIAL,NAME,ADB_PORT)

class APITest(unittest.TestCase):
    def test_target_has_private_identity(self):
        self.assertEqual(SERIAL,"emulator-5586")
        self.assertEqual(ADB_PORT,"5049")
        self.assertEqual(NAME,"APKStudio_API35")
    def test_local_profile_settings_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder)
            save_settings({"sdk_root":r"C:\Tools\Sdk","java_home":""},root)
            self.assertEqual(load_settings(root)["sdk_root"],r"C:\Tools\Sdk")
            self.assertTrue((root/"settings.json").is_file())
    def test_apk_validation_without_install(self):
        with tempfile.TemporaryDirectory() as folder:
            base=pathlib.Path(folder)
            valid=base/"ok.apk"
            with zipfile.ZipFile(valid,"w") as z:z.writestr("AndroidManifest.xml",b"manifest")
            r=inspect_apk(valid)
            self.assertEqual(r.path,valid.resolve())
            bad=base/"bad.apk";bad.write_bytes(b"not-an-apk")
            with self.assertRaises(ValueError):inspect_apk(bad)
    def test_unowned_emulator_never_gets_install(self):
        b=Bridge("C:/nothing")
        with patch.object(b,"validate",return_value=None),patch.object(b,"owned",return_value=False):
            with self.assertRaises(RuntimeError):b.command("install","some.apk")
    def test_unowned_emulator_never_gets_shutdown(self):
        b=Bridge("C:/nothing")
        with patch.object(b,"validate",return_value=None),patch.object(b,"owned",return_value=False):
            with self.assertRaises(RuntimeError):b.stop()
    def test_start_requires_ram(self):
        b=Bridge("C:/nothing")
        with patch.object(b,"validate",return_value=None),patch.object(b,"owned",return_value=False),patch.object(b,"avd_exists",return_value=True),patch.object(b,"_port_free",create=True,return_value=True):
            # No executable invoked: RAM check is mocked low
            with patch("core.free_ram_gb",return_value=2):
                with self.assertRaises(RuntimeError):b.start()
    def test_restricts_android_key_codes(self):
        b=Bridge("C:/nothing")
        with self.assertRaises(ValueError):b.key(200)

if __name__=="__main__":unittest.main(verbosity=2)
