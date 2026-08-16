import os
import argparse
from pathlib import Path
from src.misc.constants import IMAGE_COLUMNS, IMAGE_EXTENSIONS, YOLO_MODEL_PATH, YOLO_TO_PDB, YOLO_TRACKER, IMAGE_OUTPUT_FORMAT
from ultralytics import YOLO
from ultralytics.engine.results import Results as UltralyticsResults
from src.misc.io import (
    get_filenames_and_paths,
    load_metadata,
    safe_makedirs,
)


def _parse_arguements():
    # parse args
    parser = argparse.ArgumentParser(description="Save YOLO detection and tracking results on camera images.")
    parser.add_argument(
        "data_dir_path",
        type=str,
        help="Path to the directory containing all data.",
    )
    parser.add_argument(
        "img_rpath_index",
        type=str,
        help="Index of image relative path in metadata.",
    )
    args = parser.parse_args()

    # extract parameters
    data_dir_path = os.environ.get("DATA_DIR_PATH", args.data_dir_path)
    img_rpath_index = int(os.environ.get("IMG_RPATH_INDEX", args.img_rpath_index))

    return data_dir_path, img_rpath_index


def _load_yolo_model(model_path) -> YOLO:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    model_path = os.path.join(PROJECT_ROOT, model_path)

    # model exists 
    if os.path.isfile(model_path):
        print(f"Loading existing model: {model_path}")
        return YOLO(str(model_path), verbose=False)

    # download model
    model = YOLO(str(model_path), verbose=False)

    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Ultralytics did not create the expected model file: {model_path}")

    return model


def _get_cam_results(img_paths: str) -> list[UltralyticsResults]:
    model = _load_yolo_model(YOLO_MODEL_PATH)
    results: list[UltralyticsResults] = model.track(img_paths, tracker=YOLO_TRACKER)
    return results


def _convert_results(
    dir_name: str,
    timestamp_results: list[tuple[str, UltralyticsResults]],
    driver_id: int,
) -> list[dict]:
    
    detections = []

    for result_i, (timestamp, result) in enumerate(timestamp_results):
        for box_i, box in enumerate(result.boxes):
            # check if useful detection
            agent_type_id = int(box.cls[0].item())
            if result.names[agent_type_id] not in YOLO_TO_PDB:
                continue

            detections.append(
                {
                    "camera_name": dir_name,
                    "driver_id": driver_id,
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
    driver_id: int,
) -> list[list]:
    rows = _convert_results(dir_name, results, driver_id)

    return [IMAGE_COLUMNS] + [[row[column] for column in IMAGE_COLUMNS] for row in rows]


def _convert_results_to_parquet(
    dir_name: str,
    results: list[tuple[str, UltralyticsResults]],
    driver_id: int,
) -> list[dict]:
    return _convert_results(dir_name, results, driver_id)


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
                ("driver_id", pa.int64()),
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


def main():
    data_dir_path, img_rpath_index = _parse_arguements()
    metadata = load_metadata(data_dir_path)
    img_dir_rpath = metadata["image_rpaths"][img_rpath_index]

    # run yolo
    img_dir_path = os.path.join(data_dir_path, img_dir_rpath)
    timestamps, img_paths = get_filenames_and_paths(img_dir_path, IMAGE_EXTENSIONS)

    assert len(img_paths) > 0, f"No image files in {data_dir_path}'s {img_rpath_index}th image directory path"

    cam_results = _get_cam_results(img_paths)
    all_results = list(zip(timestamps, cam_results))

    # format & save results
    write_path = os.path.join("data/processed", img_dir_rpath)
    if IMAGE_OUTPUT_FORMAT in ("csv", "both"):
        csv_results = _convert_results_to_csv(img_dir_rpath, all_results, metadata["driver_id"])
        _write_csv(os.path.join(write_path, "image.csv"), csv_results)

    if IMAGE_OUTPUT_FORMAT in ("parquet", "both"):
        parquet_results = _convert_results_to_parquet(img_dir_rpath, all_results, metadata["driver_id"])
        _write_parquet(os.path.join(write_path, "image.parquet"), parquet_results)


if __name__ == "__main__":
    main()