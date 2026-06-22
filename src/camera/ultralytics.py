import os
from src.misc.time import get_ns_timestamp
from ultralytics.engine.results import Results as UltralyticsResults

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


def _get_img_timestamps_paths(img_dir_path: str) -> list[str]:
	filenames = sorted([
		f for f in os.listdir(img_dir_path)
		if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
	])

	timestamps = [get_ns_timestamp(f) for f in filenames]
	img_paths = [os.path.join(img_dir_path, f) for f in filenames]

	return timestamps, img_paths


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

	os.makedirs(os.path.dirname(path), exist_ok=True)

	with open(path, "w", newline="") as f:
		writer = csv.writer(f)
		writer.writerows(rows)


def _write_parquet(path: str, rows: list[dict]):
	import pyarrow as pa
	import pyarrow.parquet as pq

	os.makedirs(os.path.dirname(path), exist_ok=True)

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
	timestamps, img_paths = _get_img_timestamps_paths(img_source_path)

	cam_results = _get_cam_results(img_paths)

	results = list(zip(timestamps, cam_results))

	print("testing", results[8][1].boxes)

	cleaned_img_source_path = img_source_path
	if cleaned_img_source_path.startswith("data/raw/"):
		cleaned_img_source_path = cleaned_img_source_path[len("data/raw/") :]
	base_path = f"data/processed/camera/{cleaned_img_source_path}"

	# format & save results
	if output_format in ("csv", "both"):
		csv_results = _convert_results_to_csv(cleaned_img_source_path, results)
		_write_csv(os.path.join(base_path, "camera.csv"), csv_results)

	if output_format in ("parquet", "both"):
		parquet_results = _convert_results_to_parquet(cleaned_img_source_path, results)
		_write_parquet(os.path.join(base_path, "camera.parquet"), parquet_results)
