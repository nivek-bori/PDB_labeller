import os
import json
import argparse
from pathlib import Path
from src.misc.io import get_filenames_and_paths, safe_makedirs

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


def _parse_arguments():
    parser = argparse.ArgumentParser(description="Format AB3DMOT output.")

    parser.add_argument("lidar_rpath_index", type=int, help="Index of lidar relative path in metadata.")
    args = parser.parse_args()

    lidar_rpath_index = int(os.environ.get("lidar_rpath_index", args.lidar_rpath_index))

    return lidar_rpath_index


def _load_lidar_track_data() -> list[list[str | int | float]]:
    ab3dmot_dir_path = WORKSPACE_ROOT / "data/intermediate/ab3dmot"

    # frame -> timestamp
    with open(ab3dmot_dir_path / "frame_map.json", "r") as f:
        frame_map = json.load(f)

    data = []

    frames, frame_paths = get_filenames_and_paths(ab3dmot_dir_path / "detection_results/pointpillars_test_H1/trk_withid_0", ["txt"])

    for frame, frame_path in zip(frames, frame_paths):
        timestamp = int(frame_map[str(frame)])

        with open(frame_path, "r") as f:
            for line in f:
                values = line.split()
                if not values:
                    continue

                row = [
                    timestamp,  # timestamp
                    int(values[16]),  # track_id
                    values[0],  # class_id
                    float(values[8]),  # h
                    float(values[9]),  # w
                    float(values[10]),  # l
                    float(values[11]),  # x
                    float(values[12]),  # y
                    float(values[13]),  # z
                    float(values[14]),  # theta
                    float(values[15]),  # score
                ]

                data.append(row)

    return data


def _write_txt_file(write_path: str, data: list):
    safe_makedirs(write_path)
    with open(write_path, "w") as f:
        f.writelines(" ".join(str(x) for x in row) + "\n" for row in data)


def main():
    lidar_rpath_index = _parse_arguments()

    lidar_track_data = _load_lidar_track_data()

    write_path = WORKSPACE_ROOT / f"data/intermediate/lidar/track_{lidar_rpath_index}.txt"
    _write_txt_file(write_path, lidar_track_data)


if __name__ == "__main__":
    main()
