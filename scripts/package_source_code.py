"""
Package clean source code into deliverables/02_Source_Code/SANKET_Source.zip.
Excludes node_modules, .git, __pycache__, dist, build, .pytest_cache, virtualenvs, etc.
"""

import os
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "deliverables" / "02_Source_Code"
OUT_ZIP = OUT_DIR / "SANKET_Source.zip"

EXCLUDE_DIRS = {
    "node_modules",
    "__pycache__",
    ".git",
    ".pytest_cache",
    "build",
    "dist",
    "deliverables",
    ".agentic-awesome-skills",
    "graphify-out",
    "output",
    "audit",
    ".venv",
    "venv",
    "env",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".tmp",
}

INCLUDE_DIRS = [
    "src",
    "frontend",
    "scenarios",
    "scripts",
    "installer",
    "models",
    "docs",
    "datasets",
    "App_Logo_Assets_Final",
    "Videos",
]

INCLUDE_ROOT_FILES = [
    "README.md",
    "requirements.txt",
    "pytest.ini",
    "pyrefly.toml",
    "sanket.spec",
    "lr_model.json",
    "run_sanket.bat",
    ".gitignore",
    ".graphifyignore",
]

def should_exclude(rel_path: Path) -> bool:
    for part in rel_path.parts:
        if part in EXCLUDE_DIRS:
            return True
        if part.startswith(".") and part not in {".gitignore", ".graphifyignore"}:
            return True
    if rel_path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return True
    # In frontend, exclude frontend/dist
    if len(rel_path.parts) >= 2 and rel_path.parts[0] == "frontend" and rel_path.parts[1] == "dist":
        return True
    return False

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUT_ZIP.exists():
        OUT_ZIP.unlink()

    file_count = 0
    total_uncompressed_bytes = 0

    print(f"Creating source archive: {OUT_ZIP}...")
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Add root files
        for rf_name in INCLUDE_ROOT_FILES:
            rf = PROJECT_ROOT / rf_name
            if rf.is_file():
                zf.write(rf, rf_name)
                file_count += 1
                total_uncompressed_bytes += rf.stat().st_size
                print(f"  + Added root file: {rf_name}")

        # 2. Add directories
        for d_name in INCLUDE_DIRS:
            d_path = PROJECT_ROOT / d_name
            if not d_path.exists():
                continue
            for root, dirs, files in os.walk(d_path):
                # Filter dirs in-place to avoid descending into excluded directories
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
                for f in files:
                    file_path = Path(root) / f
                    rel_path = file_path.relative_to(PROJECT_ROOT)
                    if should_exclude(rel_path):
                        continue
                    zf.write(file_path, str(rel_path).replace("\\", "/"))
                    file_count += 1
                    total_uncompressed_bytes += file_path.stat().st_size

    zip_size_bytes = OUT_ZIP.stat().st_size
    print(f"\n[SOURCE ARCHIVE CREATED]")
    print(f"  Files: {file_count}")
    print(f"  Uncompressed Size: {total_uncompressed_bytes:,} bytes")
    print(f"  Archive Size: {zip_size_bytes:,} bytes ({zip_size_bytes / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    main()
