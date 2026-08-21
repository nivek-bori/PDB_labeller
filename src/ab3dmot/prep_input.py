import os
import json
import numpy as np
import argparse
from pathlib import Path
from src.misc.io import get_filenames_and_paths, load_metadata, safe_makedirs
from src.misc.constants import OPENPCDET_TO_AB3DMOT, AB3DMOT_ID_TO_NAME

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


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


def _load_dets(detection_dir_path: str):
    timestamps, det_paths = get_filenames_and_paths(detection_dir_path, ["txt"], filename_kind="timestamp")
    frames = sorted(zip(timestamps, det_paths), key=lambda item: int(item[0]))

    frame_to_timestamp = {}
    dets_by_class_id = {1: [], 2: [], 3: []}

    for frame_id, (timestamp, det_path) in enumerate(frames):
        frame_to_timestamp[frame_id] = str(timestamp)

        if Path(det_path).stat().st_size == 0:
            continue

        dets = np.loadtxt(det_path, dtype=np.float32)

        if dets.ndim == 1:
            dets = dets[None, :]

        for det in dets:
            if det.shape[0] < 9:
                raise ValueError(f"{det_path}: expected at least 9 columns, got {det.shape[0]}")

            openpcdet_class_id = int(det[8])

            if openpcdet_class_id not in OPENPCDET_TO_AB3DMOT:
                raise ValueError(f"Unknown OpenPCDet class ID: {openpcdet_class_id}")

            ab3dmot_class_id = OPENPCDET_TO_AB3DMOT[openpcdet_class_id]
            dets_by_class_id[ab3dmot_class_id].append((frame_id, det))

    return frame_to_timestamp, dets_by_class_id


def _write_class_dets(class_id: int, class_dets: list):
    class_name = AB3DMOT_ID_TO_NAME[class_id]
    write_path = WORKSPACE_ROOT / f"AB3DMOT/data/detection_results/detection/pointpillars_{class_name}_test/0000.txt"

    safe_makedirs(write_path)

    with open(write_path, "w") as f:
        for frame_id, det in class_dets:
            # OpenPCDet
            x_lidar, y_lidar, z_center_lidar = det[0], det[1], det[2]
            l, w, h = det[3], det[4], det[5]
            heading_lidar = det[6]
            score = det[7]

            z_bottom_lidar = z_center_lidar - h / 2
            x_cam, y_cam, z_cam = -y_lidar, -z_bottom_lidar, x_lidar
            theta_cam = -heading_lidar - np.pi / 2

            row = [
                frame_id,
                class_id,
                0,
                0,
                0,
                0,  # unused 2D bbox
                score,
                h,
                w,
                l,
                x_cam,
                y_cam,
                z_cam,
                theta_cam,
                0,  # alpha/orientation placeholder
            ]

            f.write(",".join(str(value) for value in row) + "\n")


def _write_frame_map_json(write_path: str, frame_to_timestamp: dict[int, float]):
    safe_makedirs(write_path)
    with open(write_path, "w") as f:
        json.dump(
            frame_to_timestamp,
            f,
            indent=2,
        )


def main():
    data_dir_path, lidar_rpath_index = _parse_arguments()
    metadata = load_metadata(data_dir_path)

    detection_dir_path = WORKSPACE_ROOT / "data/intermediate" / metadata["unique_name"] / f"lidar/detections_{lidar_rpath_index}/detections"
    frame_to_timestamp, dets_by_class_id = _load_dets(detection_dir_path)

    frame_map_path = WORKSPACE_ROOT / "data/intermediate" / metadata["unique_name"] / f"lidar/detections_{lidar_rpath_index}/frame_map.json"

    for ab3dmot_class_id, class_dets in dets_by_class_id.items():
        _write_class_dets(ab3dmot_class_id, class_dets)

    _write_frame_map_json(frame_map_path, frame_to_timestamp)


if __name__ == "__main__":
    main()
