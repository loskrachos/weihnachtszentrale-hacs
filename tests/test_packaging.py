"""Reproduce stale same-size Python bytecode after fixed-date ZIP upgrades."""
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import os
import py_compile
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).parents[1]


class PackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = json.loads((ROOT / 'release.json').read_text())
        subprocess.run([sys.executable, str(ROOT / 'scripts/build_zip.py')], check=True, capture_output=True)
        cls.archive = ROOT / 'artifacts' / ('weihnachtszentrale_v' + cls.release['version'] + '.zip')

    def test_release_dates_and_clean_archive(self):
        with zipfile.ZipFile(self.archive) as z:
            expected = datetime.fromisoformat(self.release['released_at']).timetuple()[:6]
            self.assertTrue(all(x.date_time == expected for x in z.infolist()))
            self.assertFalse(any('__pycache__' in n or '.DS_Store' in n or n.endswith('.pyc') for n in z.namelist()))

    def test_same_size_old_bytecode_is_recompiled_with_new_release_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'sample.py'
            old_time = datetime(1980, 1, 1).timestamp()
            source.write_text("VERSION = '0.5.0'\n")
            os.utime(source, (old_time, old_time))
            py_compile.compile(str(source), doraise=True)
            # The broken packaging leaves old bytecode valid after a same-size edit.
            source.write_text("VERSION = '0.9.0'\n")
            os.utime(source, (old_time, old_time))
            loader = importlib.util.spec_from_file_location('sample', source).loader
            values = {}
            exec(loader.get_code('sample'), values)
            self.assertEqual(values['VERSION'], '0.5.0')
            # The new archive's actual file date makes the cache invalid.
            with zipfile.ZipFile(self.archive) as z:
                new_time = datetime(*z.getinfo('custom_components/weihnachtszentrale/actions.py').date_time).timestamp()
            os.utime(source, (new_time, new_time))
            values = {}
            exec(loader.get_code('sample'), values)
            self.assertEqual(values['VERSION'], '0.9.0')
