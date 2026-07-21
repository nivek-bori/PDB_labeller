import os
import numpy as np
from src.misc.constants import (
		LIDAR_EXTENSIONS,
		LIDAR_POINT_DIM,
		LIDAR_RANGE_PERCENTILES,
)
from src.openpcdet.yaml_configs import (
		create_dataset_config,
		create_pointpillars_config,
		write_config,
)
from src.misc.io import (
		get_filenames_and_paths,
		safe_makedirs,
)


def _load_lidar_from_bin(lidar_paths: list[str]) -> list[np.ndarray]:
		lidar_dataset = []

		for path in lidar_paths:
				with open(path, "rb") as f:
						lidar_data = np.fromfile(f, dtype=np.float32).reshape(-1, LIDAR_POINT_DIM)
						lidar_dataset.append(lidar_data)

		return lidar_dataset


def _clean_lidar_dataset(lidar_dataset: list) -> list:
		for i, lidar_data in enumerate(lidar_dataset):
				lidar_dataset[i] = lidar_data[np.any(lidar_data != 0, axis=1)]

		return lidar_dataset


def _get_data_range(lidar_dataset: list) -> list:
		all_x, all_y, all_z = [], [], []

		for lidar_data in lidar_dataset:
				all_x.append(lidar_data[:, 0])
				all_y.append(lidar_data[:, 1])
				all_z.append(lidar_data[:, 2])

		xmin, xmax = np.percentile(np.concatenate(all_x), LIDAR_RANGE_PERCENTILES)
		ymin, ymax = np.percentile(np.concatenate(all_y), LIDAR_RANGE_PERCENTILES)
		zmin, zmax = np.percentile(np.concatenate(all_z), LIDAR_RANGE_PERCENTILES)

		return [float(xmin), float(ymin), float(zmin), float(xmax), float(ymax), float(zmax)]


def _write_lidar_dataset(path, timestamps: list[int], lidar_dataset: list[np.ndarray]):
    path = os.path.join(path, "points")
    for timestamp, lidar_points in zip(timestamps, lidar_dataset):
        safe_makedirs(path, exist_ok=True)
        np.save(os.path.join(path, f"{timestamp}.npy"), lidar_points)


def _write_image_sets(path, timestamps):
		txt_str = ""
		for timestamp in timestamps:
				txt_str += f"{timestamp}\n"

		safe_makedirs(path, exist_ok=True)
		with open(os.path.join(path, "val.txt"), "w") as f:
				f.write(txt_str)


def main(data_dir_path: str, lidar_dir_rpath: str):
    timestamps, lidar_paths = get_filenames_and_paths(os.path.join(data_dir_path, lidar_dir_rpath), LIDAR_EXTENSIONS)

    # load & clean data
    lidar_dataset = _load_lidar_from_bin(lidar_paths)
    lidar_dataset = _clean_lidar_dataset(lidar_dataset)
    data_range = _get_data_range(lidar_dataset)

    # paths
    write_path = "data/intermediate/points"

    # write to file
    _write_lidar_dataset(write_path, timestamps, lidar_dataset)
    _write_image_sets(write_path, timestamps)
    write_config(
        write_path,
        create_dataset_config(lidar_dir_rpath, data_range),
        create_pointpillars_config(lidar_dir_rpath, data_range),
    )


if __name__ == "__main__":
		import argparse

		# parse args
		parser = argparse.ArgumentParser(
				description="Save YOLO detection and tracking results on camera images."
		)
		parser.add_argument(
				"data_dir_path",
				type=str,
				help="Path to the directory containing all data.",
		)
		parser.add_argument(
				"lidar_dir_rpath",
				type=str,
				help="Path to the directory containing lidar (.bin) files relative to DATA_DIR_PATH.",
		)
		args = parser.parse_args()

				# extract parameters
		data_dir_path = (
				os.environ["DATA_DIR_PATH"]
				if "DATA_DIR_PATH" in os.environ
				else args.data_dir_path
		)
		lidar_dir_rpath = (
				os.environ["lidar_dir_rpath"]
				if "lidar_dir_rpath" in os.environ
				else args.lidar_dir_rpath
		)

		main(data_dir_path, lidar_dir_rpath)