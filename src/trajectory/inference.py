# TODO: essentially rewrite this entire file

import os
import csv
import numpy as np
import argparse
import json
from pathlib import Path
from datetime import datetime
from src.misc.io import load_metadata, get_filenames_and_paths
from src.trajectory.unify_time import unify_timestamps

PROJECT_ROOT = Path(__file__).resolve().parent


def _parse_arguments():
	parser = argparse.ArgumentParser(description="Smooth position using Kalman Filter. Reformat into tracker and oxt formats.")
	parser.add_argument(
		"data_dir_path",
		type=str,
		help="Path to the directory containing all data.",
	)
	args = parser.parse_args()

	# extract parameters
	data_dir_path = os.environ.get("DATA_DIR_PATH", args.data_dir_path)

	return data_dir_path


def _load_image_data():
	pass


def _load_image_csv(image_path: str) -> tuple[list[float], dict[float, list[dict]]]:
    image_time: list[float] = []
    image_data: dict[float, list[dict]] = {}

    with open(image_path, "r", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            timestamp = int(row["timestamp_ns"])

            if timestamp not in image_data:
                image_time.append(timestamp)
                image_data[timestamp] = []

            image_data[timestamp].append(
                {
                    "camera_name": row["camera_name"],
                    "driver_id": int(row["driver_id"]),
                    "frame_id": int(row["frame_id"]),
                    "cam_width": int(row["cam_width"]),
                    "cam_height": int(row["cam_height"]),
                    "agent_id": int(row["agent_id"]),
                    "agent_type": row["agent_type"],
                    "detection_id": int(row["detection_id"]),
                    "confidence": float(row["confidence"]),
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                    "w": float(row["w"]),
                    "h": float(row["h"]),
                }
            )

    return sorted(image_time), image_data


def _load_image_parquet(image_path: str) -> tuple[list[float], dict[float, list[dict]]]:
    import pyarrow.parquet as pq

    table = pq.read_table(image_path)

    image_time: list[float] = []
    image_data: dict[float, list[dict]] = {}

    for row in table.to_pylist():
        timestamp = int(row["timestamp_ns"])

        if timestamp not in image_data:
            image_time.append(timestamp)
            image_data[timestamp] = []

        image_data[timestamp].append(
            {
                "camera_name": row["camera_name"],
                "driver_id": row["driver_id"],
                "frame_id": row["frame_id"],
                "cam_width": row["cam_width"],
                "cam_height": row["cam_height"],
                "agent_id": row["agent_id"],
                "agent_type": row["agent_type"],
                "detection_id": row["detection_id"],
                "confidence": row["confidence"],
                "x": row["x"],
                "y": row["y"],
                "w": row["w"],
                "h": row["h"],
            }
        )

    return sorted(image_time), image_data


def _load_ab3dmot_data() -> tuple[list[float], dict]:
    ab3dmot_dir_path = PROJECT_ROOT / "data/intermediate/ab3dmot"

    # frame -> timestamp
    with open(ab3dmot_dir_path / "frame_map.json", "r") as f:
        frame_map = json.load(f)

    track_time: list[float] = []
    track_data: dict[float, dict] = {}

    frames, frame_paths = get_filenames_and_paths(
        ab3dmot_dir_path / "trk_withid_0",
        ["txt"],
        filename_kind="frame",
    )

    for frame, frame_path in zip(frames, frame_paths):
        timestamp = int(frame_map[str(frame)])

        track_time.append(timestamp)
        track_data[timestamp] = {}

        with open(frame_path, "r") as f:
            for line in f:
                values = line.split()
                if not values:
                    continue

                # KITTI format:
                # type trunc occ alpha bbox(4) h w l x y z ry score track_id
                track_data[timestamp] = {
                    "track_id": int(values[16]),
                    "class_id": values[0],
                    "dimensions": {
                        "h": float(values[8]),
                        "w": float(values[9]),
                        "l": float(values[10]),
                    },
                    "position": {
                        "x": float(values[11]),
                        "y": float(values[12]),
                        "z": float(values[13]),
                    },
                    "theta": float(values[14]),
                    "score": float(values[15]),
                }

    return sorted(track_time), track_data


def _load_gps_data() -> tuple[list[float], dict[float, dict]]:
	gps_path = PROJECT_ROOT / "data/intermediate/gps.csv"
	with open(gps_path, "r") as f:
		gps_data = f.read()

	gps_time: list[float] = []
	gps_data: dict[float, dict] = {}
	for row in gps_data:
		gps_time.append(row[0])
		gps_data[row[0]] = np.array(row[1:])

	return sorted(gps_time), gps_data


def _load_heartrate_data(heartrate_path: str) -> tuple[list[float], dict[float, float]]:
	heartrate_time: list[float] = []
	heartrate_data: dict[float, float] = {}

	with open(heartrate_path, "r", encoding="utf-8", newline="") as f:
		if f.readline().strip() != "sep=;":
			f.seek(0)

		reader = csv.DictReader(f, delimiter=";")

		for row in reader:
			timestamp = datetime.strptime(
				row["startdate"],
				"%Y-%m-%d %H:%M:%S %z",
			).timestamp()

			heartrate_time.append(timestamp)
			heartrate_data[timestamp] = float(row["value"])

	return sorted(heartrate_time), heartrate_data


def _linear_interpolation(src_time, src_data, ref_time):
	inter_time = []
	inter_data = {}

	src_n = len(src_time)
	src_i = 0

	for ref_t in ref_time:
		# find first source timestamp >= reference timestamp
		while src_i < src_n and src_time[src_i] < ref_t:
			src_i += 1

		# reference timestamp is after all source data
		if src_i >= src_n:
			continue

		# exact timestamp match
		if src_time[src_i] == ref_t:
			inter_time.append(ref_t)
			inter_data[ref_t] = src_data[ref_t]
			continue

		# reference timestamp is before the first source timestamp
		if src_i == 0:
			continue

		# linear interpolation
		src_t1 = src_time[src_i - 1]
		src_t2 = src_time[src_i]

		src_d1 = src_data[src_t1]
		src_d2 = src_data[src_t2]

		weight = (ref_t - src_t1) / (src_t2 - src_t1)
		inter_d = src_d1 + (src_d2 - src_d1) * weight

		inter_time.append(ref_t)
		inter_data[ref_t] = inter_d

	n_cut_off = len(ref_time) - len(inter_time)

	return inter_time, inter_data, n_cut_off


def _optimize_time(hertz=5, **time):
	pass


def main():
    data_dir_path = _parse_arguments()
    metadata = load_metadata(data_dir_path)

    image_time, image_data = _load_image_data()
    track_time, track_data = _load_ab3dmot_data()
    src_gps_time, src_gps_data = _load_gps_data()
    heartrate_time, heartrate_data = _load_heartrate_data(metadata["heartrate.csv"])

    gps_time, gps_data = _linear_interpolation(src_gps_time, src_gps_data, track_time)

    unified_time = unify_timestamps(track_time, gps_time, heartrate_time, hertz=metadata["sampling_hertz"])

	# TODO:
	# figure out what storage format i want
	# 	frame_id, unified_time, original_time, all_other_data...




if __name__ == "__main__":
	main()
