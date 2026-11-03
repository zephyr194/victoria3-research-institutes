"""Package standalone experimental mods without installing or overwriting files."""
import argparse
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate import validate


def build_archive(target, output_dir):
    if target not in ("1.13", "1.14"):
        raise ValueError(f"Unsupported target: {target}")
    validate()
    version = json.loads((ROOT / "compatibility.json").read_text())["version"]
    descriptor = f'''name="State Research Institutes {target} (Experimental)"
version="{version}"
supported_version="{target}.*"
tags={{ "Gameplay" "Buildings" }}
'''
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"ri-research-institutes-{target}-experimental.zip"
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("ri_research_institutes.mod", descriptor + 'path="mod/ri_research_institutes"\n')
        archive.writestr("ri_research_institutes/descriptor.mod", descriptor)
        for path in sorted((ROOT / "mod").rglob("*")):
            if path.is_file():
                archive.write(path, Path("ri_research_institutes") / path.relative_to(ROOT / "mod"))
        for name in ("README.md", "compatibility.json", "docs/INSTALL_TEST.zh-CN.md", "docs/DESIGN.zh-CN.md", "docs/SOURCES.md"):
            archive.write(ROOT / name, name)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=("1.13", "1.14"))
    parser.add_argument("--experimental", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    if not args.experimental:
        parser.error("Engine execution is unverified; acknowledge with --experimental")
    print(build_archive(args.target, args.output_dir))
