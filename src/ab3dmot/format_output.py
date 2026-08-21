import os
import json
import argparse
from pathlib import Path
from src.misc.io import get_filenames_and_paths, load_metadata, safe_makedirs


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
AB3DMOT_PATH = WORKSPACE_ROOT / "data/intermediate/ab3dmot"


def _parse_arguments():
    parser = argparse.ArgumentParser(description="Run AB3DMOT inferenceon detections.")
    parser.add_argument(
        "data_dir_path",
        type=str,
        help="Path to the directory containing all data.",
    )
    parser.add_argument(
        "lidar_rpath_index",
        type=int,
        help="Index of lidar relative path in metadata.",
    )
    args = parser.parse_args()

    data_dir_path = os.environ.get(
        "DATA_DIR_PATH",
        args.data_dir_path,
    )
    lidar_rpath_index = int(
        os.environ.get(
            "LIDAR_RPATH_INDEX",
            args.lidar_rpath_index,
        )
    )

    return data_dir_path, lidar_rpath_index


def _load_lidar_track_data(frame_map_path: str, track_results_dir: str) -> list[list[str | int | float]]:
    # frame -> timestamp
    with open(frame_map_path, "r") as f:
        frame_map = json.load(f)

    data = []

    frames, frame_paths = get_filenames_and_paths(track_results_dir, ["txt"], filename_kind="frame")

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


def _delete_temporary_data():
    import shutil

    ab3dmot_results_dir = WORKSPACE_ROOT / "data/intermediate/tmp_ab3dmot/detection_results"
    if os.path.exists(ab3dmot_results_dir):
        shutil.rmtree(ab3dmot_results_dir)


def main():
    data_dir_path, lidar_rpath_index = _parse_arguments()
    metadata = load_metadata(data_dir_path)

    frame_map_path = WORKSPACE_ROOT / "data/intermediate" / metadata["unique_name"] / f"lidar/detections_{lidar_rpath_index}/frame_map.json"
    track_results_dir = WORKSPACE_ROOT / "data/intermediate/tmp_ab3dmot/detection_results/pointpillars_test_H1/trk_withid_0/0000"
    lidar_track_data = _load_lidar_track_data(frame_map_path, track_results_dir)

    write_path = WORKSPACE_ROOT / "data/intermediate" / metadata["unique_name"] / f"lidar/track_{lidar_rpath_index}.txt"
    _write_txt_file(write_path, lidar_track_data)

    _delete_temporary_data()


if __name__ == "__main__":
    main()
