import os
import argparse
from pathlib import Path

from ultralytics import YOLO
from ultralytics.engine.results import Results as UltralyticsResults

from src.misc.constants import (
    IMAGE_COLUMNS,
    IMAGE_EXTENSIONS,
    IMAGE_OUTPUT_FORMAT,
    YOLO_MODEL_PATH,
    YOLO_TO_PDB,
    YOLO_TRACKER,
)
from src.misc.io import (
    get_filenames_and_paths,
    load_metadata,
    safe_makedirs,
)


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


def _parse_arguments():
    parser = argparse.ArgumentParser(description="Save YOLO detection and tracking results on camera images.")
    parser.add_argument(
        "data_dir_path",
        type=str,
        help="Path to the directory containing all data.",
    )
    parser.add_argument(
        "img_rpath_index",
        type=int,
        help="Index of image relative path in metadata.",
    )
    args = parser.parse_args()

    data_dir_path = os.environ.get(
        "DATA_DIR_PATH",
        args.data_dir_path,
    )
    img_rpath_index = int(
        os.environ.get(
            "IMG_RPATH_INDEX",
            args.img_rpath_index,
        )
    )

    return data_dir_path, img_rpath_index


def _load_image_paths(data_dir_path: str, img_rpath_index: int):
    metadata = load_metadata(data_dir_path)

    img_dir_rpath = metadata["image_rpaths"][img_rpath_index]
    img_dir_path = Path(data_dir_path) / img_dir_rpath

    timestamps, img_paths = get_filenames_and_paths(img_dir_path, IMAGE_EXTENSIONS, filename_kind="timestamp")

    if not img_paths:
        raise FileNotFoundError(f"No image files found in {img_dir_path}")

    return metadata, img_dir_rpath, timestamps, img_paths


def _load_yolo_model(model_path: str) -> YOLO:
    model_path = WORKSPACE_ROOT / model_path

    if model_path.is_file():
        print(f"Loading existing model: {model_path}")
        return YOLO(str(model_path), verbose=False)

    model = YOLO(str(model_path), verbose=False)

    if not model_path.is_file():
        raise FileNotFoundError(f"Ultralytics did not create the expected model file: {model_path}")

    return model


def _run_yolo_tracking(
    model: YOLO,
    img_paths: list[str],
) -> list[UltralyticsResults]:
    results: list[UltralyticsResults] = model.track(
        img_paths,
        tracker=YOLO_TRACKER,
    )

    return results


def _format_detections(
    img_rpath: str,
    timestamp_results: list[tuple[str, UltralyticsResults]],
    driver_id: int,
) -> list[dict]:

    detections = []

    for frame_id, (timestamp, result) in enumerate(timestamp_results):
        for detection_id, box in enumerate(result.boxes):
            yolo_class_id = int(box.cls[0].item())
            yolo_class_name = result.names[yolo_class_id]

            if yolo_class_name not in YOLO_TO_PDB:
                continue

            detections.append(
                {
                    "camera_name": img_rpath,
                    "driver_id": driver_id,
                    "timestamp_ns": int(timestamp),
                    "frame_id": frame_id,
                    "cam_width": result.orig_shape[1],
                    "cam_height": result.orig_shape[0],
                    "agent_id": int(box.id[0].item()),
                    "agent_type": YOLO_TO_PDB[yolo_class_name],
                    "detection_id": detection_id,
                    "confidence": float(box.conf[0]),
                    "x": float(box.xywh[0][0]),
                    "y": float(box.xywh[0][1]),
                    "w": float(box.xywh[0][2]),
                    "h": float(box.xywh[0][3]),
                }
            )

    return detections


def _write_csv(path: Path, detections: list[dict]):
    import csv

    safe_makedirs(path, exist_ok=True)

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=IMAGE_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(detections)


def _write_parquet(path: Path, detections: list[dict]):
    import pyarrow as pa
    import pyarrow.parquet as pq

    safe_makedirs(path, exist_ok=True)

    schema = pa.schema(
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
    )

    table = pa.Table.from_pylist(
        detections,
        schema=schema,
    )

    pq.write_table(table, path)


def _write_detections(write_path: str, detections: list[dict]):
    if IMAGE_OUTPUT_FORMAT in ("parquet", ".parquet", "both"):
        _write_parquet(f"{write_path}.parquet", detections)

    if IMAGE_OUTPUT_FORMAT in ("csv", ".csv", "both"):
        _write_csv(f"{write_path}.csv", detections)


def main():
    data_dir_path, img_rpath_index = _parse_arguments()

    metadata, img_dir_rpath, timestamps, img_paths = _load_image_paths(data_dir_path, img_rpath_index)

    model = _load_yolo_model(YOLO_MODEL_PATH)

    cam_results = _run_yolo_tracking(model, img_paths)

    timestamp_results = list(zip(timestamps, cam_results))

    detections = _format_detections(img_dir_rpath, timestamp_results, metadata["driver_id"])

    write_path = WORKSPACE_ROOT / "data/intermediate" / metadata["unique_name"] / f"images/track_{img_rpath_index}"
    _write_detections(write_path, detections)


if __name__ == "__main__":
    main()
