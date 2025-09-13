import os
import shutil
from pathlib import Path

repo_candidates = [Path("db_dev.sqlite3"), Path("db.sqlite3")]

DJANGO_DB_PATH = os.environ.get("DJANGO_DB_PATH")
if DJANGO_DB_PATH:
    target = Path(DJANGO_DB_PATH)
else:
    target = Path.home() / "fax_data" / "db_dev.sqlite3"

target.parent.mkdir(parents=True, exist_ok=True)

if target.exists():
    print(f"Target DB already exists at {target}; nothing to move.")
else:
    for src in repo_candidates:
        if src.exists() and src.is_file() and src.stat().st_size > 0:
            shutil.copy2(src, target)
            print(f"Copied {src} -> {target}")
            break
    else:
        print("No repo sqlite file to move; fresh DB will be created by migrations.")
