import os


def _load_det_results(file_path: str):
	import pickle

	with open(file_path, "rb") as f:
		results = pickle.load(f)

	return results


def main(data_dir_path: str, lid):
    raw_results = _load_det_results(os.path.join(data_dir_path, "TODO"))


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
	args = parser.parse_args()

	# extract parameters
	DATA_DIR_PATH = (
		os.environ["DATA_DIR_PATH"]
		if "DATA_DIR_PATH" in os.environ
		else args.data_dir_path
	)

	main(DATA_DIR_PATH)