"""
Normalize Cobertura <source> for Coverage Gutters.

coverage.py writes <source>/app</source> when tests run in Docker; the extension
then cannot match files under this django/ folder. Replacing that tag with
<source>.</source> makes paths relative to coverage.xml (this directory), which
matches coverageBaseDir in .vscode settings.

Run on the host after coverage.xml is written (bind-mounted from Docker):

  docker compose exec django sh -c "cd /app && coverage xml -o coverage.xml"
  python patch_coverage_xml_for_gutters.py

Or in one exec (no separate host step):

  docker compose exec django sh -c "cd /app && coverage xml -o coverage.xml && python patch_coverage_xml_for_gutters.py"

`.coveragerc` uses relative_files = True so class filenames stay thunderstore/...

This utility is listed in .coveragerc [run] omit so it is not traced and does not
appear in coverage.xml (Codecov has no per-file pragma in Python source).
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    django_root = Path(__file__).resolve().parent
    xml_path = django_root / "coverage.xml"
    if not xml_path.is_file():
        print(f"No file: {xml_path}", file=sys.stderr)
        return 1
    marker = "<source>/app</source>"
    text = xml_path.read_text(encoding="utf-8")
    if marker not in text:
        print("Nothing to patch (already local or different layout).")
        return 0
    xml_path.write_text(
        text.replace(marker, "<source>.</source>", 1),
        encoding="utf-8",
    )
    print("Patched coverage.xml: <source>/app</source> -> <source>.</source>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
