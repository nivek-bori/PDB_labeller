import os
import json
from src.misc.constants import IMAGE_EXTENSIONS, LIDAR_EXTENSIONS, METADATA_DEFAULTS, METADATA_DEFAULTS, METADATA_REQUIRED_KEYS
from src.misc.time import get_ns_timestamp
from pandas import DataFrame
from pathlib import Path
from collections.abc import Iterable


def safe_makedirs(path: str, exist_ok: bool = True):
	if os.path.splitext(path)[1]:  # has file
		path = os.path.dirname(path)

	if path:
		os.makedirs(path, exist_ok=exist_ok)


# both lidar and images
def get_filenames_and_paths(dir_path: str, valid_extensions: list[str]) -> tuple[list[str], list[str]]:
	filenames = sorted([f for f in os.listdir(dir_path) if os.path.splitext(f)[1].lower() in valid_extensions])

	timestamps = [get_ns_timestamp(f) for f in filenames]
	img_paths = [os.path.join(dir_path, f) for f in filenames]

	return timestamps, img_paths


def delete_data_intermediate_dir():
	import shutil

	intermediate_dir = "data/intermediate"
	if os.path.exists(intermediate_dir):
		shutil.rmtree(intermediate_dir)


def load_metadata(data_dir_path: str, throw_no_file_error: bool = True, use_true_path: bool = False):
	metadata_path = data_dir_path.replace("metadata.json", "")
	metadata_path = os.path.join(metadata_path, "metadata.json" if use_true_path else "full_metadata.json")

	if throw_no_file_error and not os.path.exists(metadata_path):
		raise FileNotFoundError(f"Metadata file not found at {metadata_path}")

	with open(metadata_path, "r") as f:
		metadata = json.load(f)

	# check required keys exist
	missing_keys = [key for key in METADATA_REQUIRED_KEYS if key not in metadata]
	if missing_keys:
		raise KeyError(f"Metadata missing required keys: {missing_keys}")

	return metadata


def load_csv(csv_path: str, skip_rows=0) -> DataFrame:
	import pandas as pd

	try:
		gps_dataframe = pd.read_csv(
			csv_path,
			skiprows=skip_rows,
			skipinitialspace=True,
		)
	except Exception as e:
		raise RuntimeError(f"Failed to load csv data from '{csv_path}': {e}")

	return gps_dataframe


def load_json(json_path: str):
	if not os.path.exists(json_path):
		raise FileNotFoundError(f"JSON file not found at {json_path}")

	with open(json_path, "r") as f:
		data = json.load(f)

	return data


def find_relative_dirs_with_file_types(root_path: str, valid_extensions: Iterable[str], sub_dir_rpath: str = '') -> list[str]:
	root_search_path = Path(os.path.join(root_path, sub_dir_rpath))

	if not root_search_path.exists():
		raise FileNotFoundError(f"Folder does not exist: {root_search_path}")

	if not root_search_path.is_dir():
		raise NotADirectoryError(f"Path is not a directory: {root_search_path}")

	matching_folders: list[Path] = []

	# Search current directory and all subdirectories
	for search_path in [root_search_path, *sorted(path for path in root_search_path.rglob("*") if path.is_dir())]:
		try:
			contains_matching_file = any(path.is_file() and path.suffix.lower() in valid_extensions for path in search_path.iterdir())
		except Exception:
			continue

		if contains_matching_file:
			search_rpath = search_path.relative_to(root_path)
			matching_folders.append(str(search_rpath))

	return matching_folders


def verify_data_dirs(data_dir_paths):
	issues = []

	for data_dir_path in data_dir_paths:
		# load metadata
		metadata = load_metadata(data_dir_path, throw_no_file_error=False, use_true_path=True)
		if not metadata:
			issues.append(f"[{data_dir_path}] Metadata is empty or invalid JSON.")
			continue

		# verify required keys
		missing_keys = [key for key in METADATA_REQUIRED_KEYS if key not in metadata]
		if missing_keys:
			issues.append(f"[{data_dir_path}] Metadata missing required keys: {missing_keys}")
			continue

		# fill in all defaults
		for key in METADATA_DEFAULTS.keys():
			metadata[key] = metadata.get(key, METADATA_DEFAULTS[key])

			if metadata[key] is None:  # if key or default is None, proceed to special defaults
				del metadata[key]

		# fill in special defaults
		metadata["lidar_rpaths"] = metadata.get("lidar_rpaths", find_relative_dirs_with_file_types(data_dir_path, LIDAR_EXTENSIONS, sub_dir_rpath="lidar"))
		metadata["image_rpaths"] = metadata.get("image_rpaths", find_relative_dirs_with_file_types(data_dir_path, IMAGE_EXTENSIONS, sub_dir_rpath="images"))

		# verify lidar
		if not metadata["lidar_rpaths"]:
			issues.append(f"[{data_dir_path}] Metadata 'lidar_rpaths' is empty or missing.")
		for lidar_rpath in metadata["lidar_rpaths"]:
			lidar_path = os.path.join(data_dir_path, lidar_rpath)
			if not os.path.isdir(lidar_path):
				issues.append(f"[{data_dir_path}] Lidar directory does not exist: {lidar_path}")
				continue

			lidar_files = get_filenames_and_paths(lidar_path, LIDAR_EXTENSIONS)
			if not lidar_files:
				issues.append(f"[{data_dir_path}] No lidar files with extensions {LIDAR_EXTENSIONS} found in {lidar_path}")

		# verify image
		if not metadata["image_rpaths"]:
			issues.append(f"[{data_dir_path}] Metadata 'image_rpaths' is empty or missing.")
		for image_rpath in metadata["image_rpaths"]:
			image_path = os.path.join(data_dir_path, image_rpath)
			if not os.path.isdir(image_path):
				issues.append(f"[{data_dir_path}] Image directory does not exist: {image_path}")
				continue

			image_files = get_filenames_and_paths(image_path, IMAGE_EXTENSIONS)
			if not image_files:
				issues.append(f"[{data_dir_path}] No image files with extensions {IMAGE_EXTENSIONS} found in {image_path}")

		# verify gps
		if not os.path.exists(os.path.join(data_dir_path, metadata["gps_rpath"])):
			issues.append(f"[{data_dir_path}] gps.csv not found at expected path: {metadata['gps_rpath']}")

		# verify canbus
		canbus_rpath = metadata.get("canbus_rpath", METADATA_DEFAULTS["canbus_rpath"])
		if not os.path.exists(os.path.join(data_dir_path, canbus_rpath)):
			issues.append(f"[{data_dir_path}] canbus.csv not found at expected path: {canbus_rpath}")

	# log issues
	if len(issues) > 0:
		error_log = "Data verification failed:\n" + "\n".join(issues)
		raise Exception(error_log)

	# write full metadata
	with open(os.path.join(data_dir_path, "full_metadata.json"), "w") as f:
		json.dump(metadata, f, indent=4)
