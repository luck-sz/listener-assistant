from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    dist_dir = Path(sys.executable).resolve().parent
    electron = dist_dir / "electron.exe"
    app_dir = dist_dir

    if not electron.exists():
        return 1

    process = subprocess.Popen([str(electron), str(app_dir)])
    return process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
