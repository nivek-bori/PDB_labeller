import os
from src.misc.constants import (
    IMAGE_COLUMNS,
    IMAGE_EXTENSIONS,
    YOLO_MODEL_PATH,
    YOLO_TO_PDB,
    YOLO_TRACKER,
)
from ultralytics.engine.results import Results as UltralyticsResults
from src.misc.io import (
    get_filenames_and_paths,
    load_metadata,
    safe_makedirs,
)


def _load_yolo_model(model_name):
    from ultralytics import YOLO
    from ultralytics.utils import LOGGER

    LOGGER.setLevel("ERROR")

    model = YOLO(model_name, verbose=False)
    model.eval()
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
    rows = _convert_results(dir_name, results)

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


def main(data_dir_path: str, img_source_path: str, output_format: str = "parquet"):
    metadata = load_metadata(data_dir_path)

    # run yolo
    timestamps, img_paths = get_filenames_and_paths(
        os.path.join(data_dir_path, img_source_path), IMAGE_EXTENSIONS
    )

    cam_results = _get_cam_results(img_paths)
    all_results = list(zip(timestamps, cam_results))

    # format & save results
    write_path = os.path.join("data/processed", img_source_path)
    if output_format in ("csv", "both"):
        csv_results = _convert_results_to_csv(
            img_source_path, all_results, metadata["driver_id"]
        )
        _write_csv(os.path.join(write_path, "image.csv"), csv_results)

    if output_format in ("parquet", "both"):
        parquet_results = _convert_results_to_parquet(
            img_source_path, all_results, metadata["driver_id"]
        )
        _write_parquet(os.path.join(write_path, "image.parquet"), parquet_results)


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
    parser.add_argument(
        "img_source_path",
        type=str,
        help="Path to the directory containing image files relative to DATA_DIR_PATH.",
    )
    args = parser.parse_args()

    # extract parameters
    DATA_DIR_PATH = (
        os.environ["DATA_DIR_PATH"]
        if "DATA_DIR_PATH" in os.environ
        else args.data_dir_path
    )
    IMG_SOURCE_PATH = (
        os.environ["IMG_SOURCE_PATH"]
        if "IMG_SOURCE_PATH" in os.environ
        else args.img_source_path
    )

    main(DATA_DIR_PATH, IMG_SOURCE_PATH)
