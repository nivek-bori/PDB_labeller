import os
import numpy as np
from src.openpcdet.yaml_configs import (
		create_dataset_config,
		create_pointpillars_config,
		write_config,
)
from src.misc.io import (
		get_data_dir_relative_path,
		get_timestamps_and_paths,
		safe_makedirs,
)


def _load_lidar_from_bin(lidar_paths: list[str]) -> list[np.ndarray]:
		lidar_dataset = []

		for path in lidar_paths:
				with open(path, "rb") as f:
						lidar_data = np.fromfile(f, dtype=np.float32).reshape(-1, 4)
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

		xmin, xmax = np.percentile(np.concatenate(all_x), [0.1, 99.9])
		ymin, ymax = np.percentile(np.concatenate(all_y), [0.1, 99.9])
		zmin, zmax = np.percentile(np.concatenate(all_z), [0.1, 99.9])

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


def preprocess(lidar_source_path: str):
		timestamps, lidar_paths = get_timestamps_and_paths(lidar_source_path, [".bin"])

		# load & clean data
		lidar_dataset = _load_lidar_from_bin(lidar_paths)
		lidar_dataset = _clean_lidar_dataset(lidar_dataset)
		data_range = _get_data_range(lidar_dataset)

		# paths
		data_dir_relative_path = get_data_dir_relative_path(lidar_source_path)
		write_path = "data/intermediate/openpcdet"

		# write to file
		_write_lidar_dataset(write_path, timestamps, lidar_dataset)
		_write_image_sets(write_path, timestamps)
		write_config(
				write_path,
				create_dataset_config(data_dir_relative_path, data_range),
				create_pointpillars_config(data_dir_relative_path, data_range),
		)


if __name__ == "__main__":
		import argparse

		parser = argparse.ArgumentParser(
				description="Reformat LiDAR .bin files to .npy format."
		)
		parser.add_argument(
				"lidar_source_path",
				type=str,
				help="Path to the directory containing LiDAR .bin files.",
		)
		args = parser.parse_args()

		if "LIDAR_SOURCE_PATH" in os.environ:
				preprocess(os.environ["LIDAR_SOURCE_PATH"])
		elif args.lidar_source_path:
			preprocess(args.lidar_source_path)
		else:
			raise ValueError("LIDAR_SOURCE_PATH not provided as environment variable or arguement")
		

