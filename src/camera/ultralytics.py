import os
from ultralytics.engine.results import Results as UltralyticsResults
from src.misc.io import (
    get_timestamps_and_paths,
    get_data_dir_relative_path,
    safe_makedirs,
)

YOLO_TO_PDB = {
    "car": "Vehicle",
    "truck": "Vehicle",
    "bus": "Vehicle",
    "motorcycle": "Vehicle",
    "person": "Pedestrian",
    "bicycle": "Cyclist",
}

CAMERA_COLUMNS = [
    "camera_name",
    "timestamp_ns",
    "frame_id",
    "cam_width",
    "cam_height",
    "agent_id",
    "agent_type",
    "detection_id",
    "confidence",
    "x",
    "y",
    "w",
    "h",
]

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tiff",
    ".tif",
    ".gif",
    ".webp",
    ".ppm",
    ".pgm",
    ".pbm",
    ".pnm",
    ".ico",
    ".jfif",
    ".heic",
    ".heif",
}


def _load_yolo_model(model_name):
    from ultralytics import YOLO
    from ultralytics.utils import LOGGER

    LOGGER.setLevel("ERROR")

    model = YOLO(model_name, verbose=False)
    model.eval()
    return model


def _get_cam_results(img_paths: str) -> list[UltralyticsResults]:
	model = _load_yolo_model("models/yolo26l.pt")  # TODO: add as config

	results: list[UltralyticsResults] = model.track(img_paths, tracker="botsort.yaml")

	return results


def _convert_results(
	dir_name: str,
	timestamp_results: list[tuple[str, UltralyticsResults]],
) -> list[dict]:
	detections = []

	for result_i, (timestamp, result) in enumerate(timestamp_results):
		for box_i, box in enumerate(result.boxes):
			agent_type_id = int(box.cls[0].item())
			if result.names[agent_type_id] not in YOLO_TO_PDB: # check if useful detection
				continue

			detections.append(
				{
					"camera_name": dir_name,
					"timestamp_ns": int(timestamp),
					"frame_id": result_i,
					"cam_width": result.orig_shape[0],
					"cam_height": result.orig_shape[1],
					"agent_id": int(box.id[0].item()),
					"agent_type": YOLO_TO_PDB[result.names[agent_type_id]],
					"detection_id": box_i,
					"confidence": float(box.conf[0]),
					"x": float(box.xywh[0][0]),
					"y": float(box.xywh[0][1]),
					"w": float(box.xywh[0][2]),
					"h": float(box.xywh[0][3]),
				}
			)

	return detections


def _convert_results_to_csv(
	dir_name: str,
	results: list[tuple[str, UltralyticsResults]],
) -> list[list]:
	rows = _convert_results(dir_name, results)

	return [CAMERA_COLUMNS] + [
		[row[column] for column in CAMERA_COLUMNS] for row in rows
	]


def _convert_results_to_parquet(
	dir_name: str,
	results: list[tuple[str, UltralyticsResults]],
) -> list[dict]:
	return _convert_results(dir_name, results)


def _write_csv(path: str, rows: list):
    import csv

    safe_makedirs(path, exist_ok=True)

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def _write_parquet(path: str, rows: list[dict]):
    import pyarrow as pa
    import pyarrow.parquet as pq

    safe_makedirs(path, exist_ok=True)

    table = pa.Table.from_pylist(
        rows,
        schema=pa.schema(
            [
                ("camera_name", pa.string()),
                ("timestamp_ns", pa.int64()),
                ("frame_id", pa.int64()),
                ("cam_width", pa.int64()),
                ("cam_height", pa.int64()),
                ("agent_id", pa.int64()),
                ("agent_type", pa.string()),
                ("detection_id", pa.int64()),
                ("confidence", pa.float64()),
                ("x", pa.float64()),
                ("y", pa.float64()),
                ("w", pa.float64()),
                ("h", pa.float64()),
            ]
        ),
    )
    pq.write_table(table, path)


def track_2d(img_source_path: str, output_format: str = "parquet"):
    # run yolo
    timestamps, img_paths = get_timestamps_and_paths(img_source_path, IMAGE_EXTENSIONS)

    cam_results = _get_cam_results(img_paths)

    results = list(zip(timestamps, cam_results))

    data_dir_relative_path = get_data_dir_relative_path(img_source_path)
    write_path = os.path.join("data/processed/camera", data_dir_relative_path)

    # format & save results
    if output_format in ("csv", "both"):
        csv_results = _convert_results_to_csv(data_dir_relative_path, results)
        _write_csv(os.path.join(write_path, "camera.csv"), csv_results)

    if output_format in ("parquet", "both"):
        parquet_results = _convert_results_to_parquet(data_dir_relative_path, results)
        _write_parquet(os.path.join(write_path, "camera.parquet"), parquet_results)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Save YOLO detection and tracking results on camera images."
    )
    parser.add_argument(
        "img_source_path",
        type=str,
        help="Path to the directory containing image files.",
    )
    args = parser.parse_args()

    if "IMG_SOURCE_PATH" in os.environ:
        track_2d(os.environ["IMG_SOURCE_PATH"])
    else:
        track_2d(args.img_source_path)