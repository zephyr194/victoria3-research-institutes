import importlib.util
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ri_package", ROOT / "scripts/package.py")
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class PackagingTests(unittest.TestCase):
    def test_both_targets_are_complete_standalone_archives(self):
        with tempfile.TemporaryDirectory() as output:
            for target in ("1.13", "1.14"):
                with self.subTest(target=target), ZipFile(package.build_archive(target, output)) as archive:
                    names = archive.namelist()
                    self.assertEqual(len(names), len(set(names)))
                    self.assertIsNone(archive.testzip())
                    outer = archive.read("ri_research_institutes.mod").decode()
                    inner = archive.read("ri_research_institutes/descriptor.mod").decode()
                    self.assertIn(f'supported_version="{target}.*"', inner)
                    self.assertEqual(outer, inner + 'path="mod/ri_research_institutes"\n')
                    for path in (ROOT / "mod").rglob("*"):
                        if path.is_file():
                            name = str(Path("ri_research_institutes") / path.relative_to(ROOT / "mod"))
                            self.assertEqual(archive.read(name), path.read_bytes())
                    self.assertIn("docs/INSTALL_TEST.zh-CN.md", names)


if __name__ == "__main__":
    unittest.main()
