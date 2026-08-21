import os
import argparse
from pathlib import Path
import numpy as np
from src.misc.constants import (
    LIDAR_EXTENSIONS,
    LIDAR_POINT_DIM,
    LIDAR_RANGE_PERCENTILES,
    POINTPILLARS_POINT_CLOUD_RANGE,
)
from src.openpcdet.yaml_configs import (
    create_dataset_config,
    create_pointpillars_config,
    write_config,
)
from src.misc.io import (
    get_filenames_and_paths,
    safe_makedirs,
    load_metadata
)


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


def _parse_arguments():
    # parse args
    parser = argparse.ArgumentParser(description="Save YOLO detection and tracking results on camera images.")
    parser.add_argument(
        "data_dir_path",
        type=str,
        help="Path to the directory containing all data.",
    )
    parser.add_argument(
        "lidar_rpath_index",
        type=str,
        help="Index of lidar relative path in metadata.",
    )
    args = parser.parse_args()

    # Extract parameters
    data_dir_path = os.environ.get("DATA_DIR_PATH", args.data_dir_path)
    lidar_rpath_index = int(os.environ.get("LIDAR_RPATH_INDEX", args.lidar_rpath_index))

    return data_dir_path, lidar_rpath_index


def _load_lidar_from_bin(lidar_paths: list[str]) -> list[np.ndarray]:
    lidar_dataset = []

    for path in lidar_paths:
        with open(path, "rb") as f:
            lidar_data = np.fromfile(f, dtype=np.float32).reshape(-1, LIDAR_POINT_DIM)
            lidar_dataset.append(lidar_data)

    return lidar_dataset


def _process_lidar_dataset(lidar_dataset: list, lidar_transformation: list) -> list:
    transformation = np.asarray(lidar_transformation, dtype=np.float32)
    valid_transformation = not np.allclose(transformation, 0)

    processed = []

    for lidar_data in lidar_dataset:
        lidar_data = np.asarray(lidar_data)

        # remove non-zeros
        lidar_data = lidar_data[np.any(lidar_data != 0, axis=1)]

        # transformation
        if valid_transformation:
            lidar_data = lidar_data.copy()
            lidar_data[:, :3] += transformation

        # Keep only points with valid Z.
        z = lidar_data[:, 2]
        valid = (z >= -1.0) & (z <= 3.0)
        lidar_data = lidar_data[valid]

        processed.append(lidar_data)

    return processed


def _write_lidar_dataset(dir_path, timestamps: list[int], lidar_dataset: list[np.ndarray]):
    dir_path = os.path.join(dir_path, "points")
    safe_makedirs(dir_path, exist_ok=True)

    for timestamp, lidar_points in zip(timestamps, lidar_dataset):
        np.save(os.path.join(dir_path, f"{timestamp}.npy"), lidar_points)


def main():
    data_dir_path, lidar_rpath_index = _parse_arguments()
    metadata = load_metadata(data_dir_path)
    lidar_dir_rpath = metadata["lidar_rpaths"][lidar_rpath_index]
    lidar_transformation = metadata["lidar_transformations"][lidar_rpath_index]
    
    # lidar paths
    lidar_dir_path = os.path.join(data_dir_path, lidar_dir_rpath)
    timestamps, lidar_paths = get_filenames_and_paths(lidar_dir_path, LIDAR_EXTENSIONS, filename_kind="timestamp")

    # load & clean data
    lidar_dataset = _load_lidar_from_bin(lidar_paths)
    lidar_dataset = _process_lidar_dataset(lidar_dataset, lidar_transformation)

    # paths
    write_dir_path = WORKSPACE_ROOT / "data/intermediate" / metadata["unique_name"] / f"lidar/detections_{lidar_rpath_index}"

    # write to file
    _write_lidar_dataset(write_dir_path, timestamps, lidar_dataset)
    write_config(
        write_dir_path,
        create_dataset_config(lidar_dir_rpath, POINTPILLARS_POINT_CLOUD_RANGE),
        create_pointpillars_config(write_dir_path, POINTPILLARS_POINT_CLOUD_RANGE),
    )


if __name__ == "__main__":
    main()
