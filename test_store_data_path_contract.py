"""Lock the shipped device/register/export contract documented in store.js."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
STORE = (ROOT / "assets" / "store.js").read_text(encoding="utf-8")
FB = (ROOT / "assets" / "fb.js").read_text(encoding="utf-8")


class StoreDataPathContractTests(unittest.TestCase):
    def test_header_describes_the_register_bridge_not_a_local_only_store(self):
        header = STORE.split("===================================================================== */", 1)[0]
        self.assertIn("syncToRegister()", header)
        self.assertIn("submissions", header)
        self.assertNotIn("Deliberately has NO backend", header)
        self.assertNotIn("leave it only when a person exports them", header)

    def test_save_writes_the_device_copy_before_syncing(self):
        save = re.search(r"function save\(rec\) \{([\s\S]*?)\n\}", STORE)
        assert save is not None
        body = save.group(1)
        self.assertLess(body.index("write(list)"), body.index("syncToRegister(out)"))

    def test_focal_point_is_stripped_from_network_but_kept_in_export(self):
        never_sent = re.search(r"var NEVER_SENT = \[([\s\S]*?)\];", FB)
        assert never_sent is not None
        csv_columns = re.search(r"const CSV_COLUMNS = \[([\s\S]*?)\];", STORE)
        assert csv_columns is not None
        for key in ("focalName", "focalPhone", "focalEmail"):
            self.assertIn(f'"{key}"', never_sent.group(1))
            self.assertIn(f'"{key}"', csv_columns.group(1))


if __name__ == "__main__":
    unittest.main()
