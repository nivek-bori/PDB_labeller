import os
from src.misc.time import get_ns_timestamp


def safe_makedirs(path: str, exist_ok: bool = True):
    if os.path.splitext(path)[1]:  # has file
        path = os.path.dirname(path)

    if path:
        os.makedirs(path, exist_ok=exist_ok)


def get_data_dir_relative_path(path: str) -> str:
    """
    Returns everything after "data/raw" or "data/processed".
    """
    import re

    m = re.search(r"(data/raw|data/processed)(.*)", path)
    if m:
        return m.group(2).lstrip("/\\")
    return path


def get_full_path(path: str) -> str:
    if "data/" in path or "data\\\\" in path:
        return path
    elif path.startswith("raw"):
        return os.path.join("data", path)
    else:
        return os.path.join("data/raw", path)


def get_timestamps_and_paths(
    dir_path: str, valid_extensions: list[str]
) -> tuple[list[str], list[str]]:
    dir_path = get_full_path(dir_path)

    filenames = sorted(
        [
            f
            for f in os.listdir(dir_path)
            if os.path.splitext(f)[1].lower() in valid_extensions
        ]
    )

    timestamps = [get_ns_timestamp(f) for f in filenames]
    img_paths = [os.path.join(dir_path, f) for f in filenames]

    return timestamps, img_paths