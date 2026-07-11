import os
from src.misc.time import get_ns_timestamp


def safe_makedirs(path: str, exist_ok: bool = True):
    if os.path.splitext(path)[1]:  # has file
        path = os.path.dirname(path)

    if path:
        os.makedirs(path, exist_ok=exist_ok)


# both lidar and images
def get_filenames_and_paths(
    dir_path: str, valid_extensions: list[str]
) -> tuple[list[str], list[str]]:
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


def delete_data_intermediate_dir():
    import shutil

    intermediate_dir = "data/intermediate"
    if os.path.exists(intermediate_dir):
        shutil.rmtree(intermediate_dir)


def load_metadata(data_dir_path: str, throw_no_file_error: bool = True):
    import json

    if os.path.isdir(data_dir_path):
        metadata_path = os.path.join(data_dir_path, "metadata.json")
    else:
        metadata_path = data_dir_path

    if throw_no_file_error and not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found at {metadata_path}")

    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    return metadata
