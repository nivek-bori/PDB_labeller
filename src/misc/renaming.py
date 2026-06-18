"""
This script assists the user in batch-renaming files with names that contain Unix epoch timestamps 
within specified directories. It guides the user to enter one or more root directories, then finds 
subdirectories containing files, previews sample files per directory, and requires user approval 
before proceeding. For each approved directory, files with epoch-based names are renamed to a 
human-readable format (YYYY-MM-DD_HHMMSS_[fractional][remainder]), avoiding naming conflicts.
"""

import os
import re
from datetime import datetime

EPOCH_FILENAME_RE = re.compile(r"^(\d{10})(?:\.(\d+))?(.*)$")


def _get_user_roots() -> list[str]:
    print("Enter root directory paths, separated by semicolons ';' (all on one line):")
    roots: list[str] = []
    line = input("> ").strip()
    if line:
        for path in map(str.strip, line.split(';')):
            if not path:
                continue
            path = os.path.expanduser(path)
            if os.path.isdir(path):
                roots.append(os.path.abspath(path))
            else:
                print(f"  Skipping: not a directory: {path}")
    return roots


def _get_has_file_dir_paths(roots: list[str]) -> list[str]:
    """Return a list of paths to directories under the root with files inside them"""
    dir_paths: list[str] = []
    seen_paths: set[str] = set()
    for root in roots:
        for dirpath, _, filenames in os.walk(root):
            if not filenames: # assert files exist
                continue
            abspath = os.path.abspath(dirpath)
            if abspath in seen_paths:
                continue
            seen_paths.add(abspath)
            dir_paths.append(abspath)
    return sorted(dir_paths)


def _get_user_approval(dir_paths: list[str]) -> list[str]:
    """Present path & 10 files inside path to user. Remove paths that the user rejects"""
    approved: list[str] = []
    for dir_path in dir_paths:
        files = sorted(
            name
            for name in os.listdir(dir_path)
            if os.path.isfile(os.path.join(dir_path, name))
        )
        print(f"\nDirectory: {dir_path}")
        print("Sample files:")
        for name in files[:10]:
            print(f"  {name}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")

        while True:
            answer = input("Approve this directory? [y/n]: ").strip().lower()
            if answer in ("y", "yes"):
                approved.append(dir_path)
                break
            if answer in ("n", "no"):
                break
            print("Please enter y or n.")
    return approved


def _format_epoch_filename(name: str) -> str | None:
    stem, ext = os.path.splitext(name)
    match = EPOCH_FILENAME_RE.match(stem)
    if not match:
        return None

    seconds_str, fractional, remainder = match.groups()
    try:
        dt = datetime.fromtimestamp(int(seconds_str))
    except (OSError, OverflowError, ValueError):
        return None

    formatted = dt.strftime("%Y-%m-%d_%H%M%S")
    if fractional:
        formatted += f"_{fractional}"
    formatted += remainder
    return formatted + ext


def _reformat_file_names(dir_path: str):
    """Rename files form time from unix epoch to YYYY-MM-DD_HHMMSS_[remaining decimal places]"""
    for name in os.listdir(dir_path):
        src = os.path.join(dir_path, name)
        if not os.path.isfile(src):
            continue

        new_name = _format_epoch_filename(name)
        if new_name is None or new_name == name:
            continue

        dst = os.path.join(dir_path, new_name)
        if os.path.exists(dst):
            print(f"  Skipping {name}: destination already exists ({new_name})")
            continue

        os.rename(src, dst)
        print(f"  Renamed: {name} -> {new_name}")


def rename_timestamp_files():
    roots = _get_user_roots()
    if not roots:
        print("No root directories provided.")
        return

    dir_paths = _get_has_file_dir_paths(roots)
    if not dir_paths:
        print("No directories with files found.")
        return

    approved_dir_paths = _get_user_approval(dir_paths)
    if not approved_dir_paths:
        print("No directories approved.")
        return

    for dir_path in approved_dir_paths:
        print(f"\nRenaming files in: {dir_path}")
        _reformat_file_names(dir_path)


if __name__ == "__main__":
    rename_timestamp_files()
