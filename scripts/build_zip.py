# -*- coding: utf-8 -*-
"""
LVT Plugin — Build ZIP for Release.

Creates a distributable ZIP file containing only the files
needed for end-user installation via QGIS Plugin Manager.

Usage:
    python build_zip.py

Output:
    LVT_v{version}.zip in the parent directory.

Author: Lộc Vũ Trung (LVT) / Slow Forest
"""

import os
import zipfile
import configparser

# Directories and files to EXCLUDE from the release ZIP
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".vscode",
    "scripts",
    ".idea",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
}


def get_version(plugin_dir):
    """Read version from metadata.txt."""
    config = configparser.ConfigParser()
    config.read(os.path.join(plugin_dir, "metadata.txt"), encoding="utf-8")
    return config.get("general", "version", fallback="0.0.0")


def should_include(path, root_dir):
    """Determine if a file/directory should be included in the ZIP."""
    rel = os.path.relpath(path, root_dir)
    parts = rel.split(os.sep)

    # Exclude blacklisted directories
    for part in parts:
        if part in EXCLUDE_DIRS:
            return False

    # Exclude by extension
    _, ext = os.path.splitext(path)
    if ext in EXCLUDE_EXTENSIONS:
        return False

    return True


def build_zip():
    """Create the release ZIP file."""
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    version = get_version(plugin_dir)
    zip_name = f"LVT_v{version}.zip"
    zip_path = os.path.join(os.path.dirname(plugin_dir), zip_name)

    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(plugin_dir):
            # Filter out excluded directories (in-place)
            dirnames[:] = [
                d for d in dirnames
                if d not in EXCLUDE_DIRS
            ]

            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if should_include(filepath, plugin_dir):
                    arcname = os.path.join(
                        "LVT",
                        os.path.relpath(filepath, plugin_dir),
                    )
                    zf.write(filepath, arcname)
                    file_count += 1

    print(f"Built: {zip_path}")
    print(f"Files: {file_count}")
    print(f"Version: {version}")


if __name__ == "__main__":
    build_zip()
