"""Download raw datasets into data/raw/.

    python scripts/download_data.py                 # all datasets implemented so far
    python scripts/download_data.py mola tes        # only some
    python scripts/download_data.py --list          # list available datasets

Safe to re-run: files already downloaded with the right size are skipped.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analogs.download import DATASETS, download  # noqa: E402


def main(argv: list[str]) -> None:
    if "--list" in argv:
        for ds in DATASETS.values():
            print(f"{ds.key:14s} {ds.body:6s} {ds.description}")
        return
    download(argv or None)


if __name__ == "__main__":
    main(sys.argv[1:])
