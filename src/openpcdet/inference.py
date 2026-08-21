import argparse
import json
import os
from pathlib import Path
from typing import Optional

import numpy as np
import torch

from pcdet.config import cfg, cfg_from_yaml_file
from pcdet.datasets import DatasetTemplate
from pcdet.models import build_network, load_data_to_gpu
from pcdet.utils import common_utils
from src.misc.io import load_metadata, safe_makedirs


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
OPENPCDET_MODEL_PATH = WORKSPACE_ROOT / "models/pointpillars.pth"


class PointCloudInferenceDataset(DatasetTemplate):
    """
    Minimal OpenPCDet dataset for inference on unlabeled point clouds.

    This intentionally does NOT use CustomDataset, ImageSets, labels,
    custom_infos_*.pkl, or a ground-truth database.
    """

    def __init__(
        self,
        dataset_cfg,
        class_names,
        root_path: Path,
        logger,
        ext: str = ".npy",
    ):
        super().__init__(
            dataset_cfg=dataset_cfg,
            class_names=class_names,
            training=False,
            root_path=root_path,
            logger=logger,
        )

        self.root_path = Path(root_path)
        self.ext = ext if ext.startswith(".") else f".{ext}"

        if self.root_path.is_file():
            if self.root_path.suffix != self.ext:
                raise ValueError(f"Input file extension {self.root_path.suffix!r} does not match --ext {self.ext!r}")
            files = [self.root_path]
        elif self.root_path.is_dir():
            files = list(self.root_path.glob(f"*{self.ext}"))
        else:
            raise FileNotFoundError(f"Point-cloud path does not exist: {self.root_path}")

        # Timestamp-like filenames should be processed numerically when possible.
        def sort_key(path: Path):
            try:
                return (0, int(path.stem))
            except ValueError:
                return (1, path.stem)

        self.sample_file_list = sorted(files, key=sort_key)

        if not self.sample_file_list:
            raise RuntimeError(f"No {self.ext} point-cloud files found in {self.root_path}")

        self.num_features = len(self.dataset_cfg.POINT_FEATURE_ENCODING.src_feature_list)

    def __len__(self):
        return len(self.sample_file_list)

    def _load_points(self, path: Path) -> np.ndarray:
        if self.ext == ".npy":
            points = np.load(path)
        elif self.ext == ".bin":
            raw = np.fromfile(path, dtype=np.float32)

            if raw.size % self.num_features != 0:
                raise ValueError(
                    f"{path} contains {raw.size} float32 values, which cannot be reshaped into points with {self.num_features} features."
                )

            points = raw.reshape(-1, self.num_features)
        else:
            raise NotImplementedError(f"Unsupported point-cloud extension: {self.ext}")

        points = np.asarray(points, dtype=np.float32)

        if points.ndim != 2:
            raise ValueError(f"{path} must contain a 2-D point array, got shape {points.shape}")

        if points.shape[1] != self.num_features:
            raise ValueError(
                f"{path} has {points.shape[1]} features per point, but the "
                f"OpenPCDet config expects {self.num_features}: "
                f"{list(self.dataset_cfg.POINT_FEATURE_ENCODING.src_feature_list)}"
            )

        # Remove padding/empty rows if the source LiDAR uses all-zero records.
        points = points[np.any(points != 0, axis=1)]

        if len(points) == 0:
            raise ValueError(f"{path} contains no non-zero points.")

        return points

    def __getitem__(self, index):
        point_path = self.sample_file_list[index]
        points = self._load_points(point_path)

        # Preserve the source filename/timestamp so predictions can be matched
        # to the original frame and later passed to a tracker.
        input_dict = {
            "points": points,
            "frame_id": point_path.stem,
        }

        return self.prepare_data(data_dict=input_dict)


def _parse_arguments():
    parser = argparse.ArgumentParser(description="Run a pretrained OpenPCDet model on unlabeled point clouds.")
    parser.add_argument(
        "data_dir_path",
        type=str,
        help="Path to the directory containing all data.",
    )
    parser.add_argument(
        "lidar_rpath_index",
        type=int,
        help="Index of LiDAR relative path in metadata.",
    )
    parser.add_argument(
        "--score_thresh",
        type=float,
        default=None,
        help=("Optional additional score threshold. If omitted, all predictions returned by the model/config are saved."),
    )
    args = parser.parse_args()

    data_dir_path = os.environ.get("DATA_DIR_PATH", args.data_dir_path)
    lidar_rpath_index = int(os.environ.get("LIDAR_RPATH_INDEX", args.lidar_rpath_index))

    return data_dir_path, lidar_rpath_index, args.score_thresh


def _get_inference_paths(data_dir_path: str, lidar_rpath_index: int):
    metadata = load_metadata(data_dir_path)

    intermediate_dir = WORKSPACE_ROOT / "data/intermediate" / metadata["unique_name"] / "lidar" / f"detections_{lidar_rpath_index}"

    return (
        intermediate_dir / "model.yaml",
        OPENPCDET_MODEL_PATH,
        intermediate_dir / "points",
        intermediate_dir / "detections",
    )


def _save_predictions(
    output_path: Path,
    frame_id: str,
    pred_dict: dict,
    class_names: list[str],
    score_thresh: Optional[float],
):
    boxes = pred_dict["pred_boxes"].detach().cpu().numpy()
    scores = pred_dict["pred_scores"].detach().cpu().numpy()
    labels = pred_dict["pred_labels"].detach().cpu().numpy().astype(np.int32)

    if score_thresh is not None:
        keep = scores >= score_thresh
        boxes = boxes[keep]
        scores = scores[keep]
        labels = labels[keep]

    # Preserve the raw OpenPCDet output exactly in a compressed NumPy file.
    np.savez_compressed(
        output_path / f"{frame_id}.npz",
        pred_boxes=boxes,
        pred_scores=scores,
        pred_labels=labels,
    )

    # Also write a simple tracker-friendly numeric text representation:
    #
    # x y z dx dy dz heading score class_id
    #
    # OpenPCDet class IDs are 1-based.
    txt_path = output_path / f"{frame_id}.txt"

    if len(boxes) == 0:
        txt_path.write_text("")
        return 0

    if boxes.shape[1] < 7:
        raise ValueError(f"Expected predicted boxes to contain at least 7 values, got {boxes.shape}")

    rows = np.column_stack(
        [
            boxes[:, :7],
            scores,
            labels,
        ]
    )

    np.savetxt(
        txt_path,
        rows,
        fmt=["%.6f"] * 8 + ["%d"],
    )

    return len(boxes)


def main():
    data_dir_path, lidar_rpath_index, score_thresh = _parse_arguments()
    cfg_file, ckpt, data_path, output_path = _get_inference_paths(
        data_dir_path,
        lidar_rpath_index,
    )

    if not cfg_file.is_file():
        raise FileNotFoundError(f"Config file does not exist: {cfg_file}")

    if not ckpt.is_file():
        raise FileNotFoundError(f"Checkpoint does not exist: {ckpt}")

    if score_thresh is not None and not 0.0 <= score_thresh <= 1.0:
        raise ValueError("--score_thresh must be between 0 and 1.")

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available inside the container. OpenPCDet inference requires the GPU in this setup.")

    cfg_from_yaml_file(str(cfg_file), cfg)

    logger = common_utils.create_logger()
    logger.info("Starting OpenPCDet inference")
    logger.info("Config: %s", cfg_file)
    logger.info("Checkpoint: %s", ckpt)
    logger.info("Point clouds: %s", data_path)

    dataset = PointCloudInferenceDataset(
        dataset_cfg=cfg.DATA_CONFIG,
        class_names=cfg.CLASS_NAMES,
        root_path=data_path,
        logger=logger,
        ext=".npy",
    )

    safe_makedirs(output_path)

    # Save the class-ID mapping once for interpreting pred_labels.
    class_map = {str(index + 1): class_name for index, class_name in enumerate(cfg.CLASS_NAMES)}
    with open(output_path / "classes.json", "w", encoding="utf-8") as f:
        json.dump(class_map, f, indent=2)

    logger.info("Total point clouds: %d", len(dataset))
    logger.info("Class mapping: %s", class_map)

    model = build_network(
        model_cfg=cfg.MODEL,
        num_class=len(cfg.CLASS_NAMES),
        dataset=dataset,
    )

    model.load_params_from_file(
        filename=str(ckpt),
        logger=logger,
        to_cpu=True,
    )

    model.cuda()
    model.eval()

    total_detections = 0

    with torch.no_grad():
        for index, data_dict in enumerate(dataset):
            frame_id = str(data_dict["frame_id"])

            batch_dict = dataset.collate_batch([data_dict])
            load_data_to_gpu(batch_dict)

            pred_dicts, _ = model.forward(batch_dict)

            if len(pred_dicts) != 1:
                raise RuntimeError(f"Expected one prediction dictionary for a one-frame batch, got {len(pred_dicts)}")

            num_detections = _save_predictions(
                output_path=output_path,
                frame_id=frame_id,
                pred_dict=pred_dicts[0],
                class_names=cfg.CLASS_NAMES,
                score_thresh=score_thresh,
            )
            total_detections += num_detections

            logger.info(
                "Frame %d/%d: %s -> %d detections",
                index + 1,
                len(dataset),
                frame_id,
                num_detections,
            )

    logger.info(
        "Inference complete: %d frames, %d total detections",
        len(dataset),
        total_detections,
    )
    logger.info("Predictions written to: %s", output_path)


if __name__ == "__main__":
    main()
