import json
import numpy as np
from pathlib import Path
from src.misc.io import get_filenames_and_paths, safe_makedirs
from src.misc.constants import OPENPCDET_TO_AB3DMOT, AB3DMOT_ID_TO_NAME


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
DETECTION_DIR = WORKSPACE_ROOT / "data/intermediate/openpcdet/detections"
AB3DMOT_DETECTION_DIR = WORKSPACE_ROOT / "AB3DMOT/data/detection_results/detection"
FRAME_MAP_PATH = WORKSPACE_ROOT / "data/intermediate/ab3dmot/frame_map.json"


def _load_dets():
		timestamps, det_paths = get_filenames_and_paths(str(DETECTION_DIR), [".txt"])

		frames = sorted(zip(timestamps, det_paths), key=lambda item: int(item[0]))

		frame_to_timestamp = {}

		dets_by_class_id = { 1: [], 2: [], 3: []}

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

		write_dir = AB3DMOT_DETECTION_DIR / f"pointpillars_{class_name}_test"
		write_path = write_dir / "0000.txt"

		safe_makedirs(write_dir)

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


def main():
		frame_to_timestamp, dets_by_class_id = _load_dets()

		for class_id, dets in dets_by_class_id.items():
				_write_class_dets(class_id, dets)

		safe_makedirs(FRAME_MAP_PATH.parent)

		with open(FRAME_MAP_PATH, "w") as f:
				json.dump(
						frame_to_timestamp,
						f,
						indent=2,
				)


if __name__ == "__main__":
		main()
