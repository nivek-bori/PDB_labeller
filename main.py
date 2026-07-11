import os
from pathlib import Path
import docker
import argparse

from src.misc.constants import (
    DOCKER_DATA_BIND,
    DOCKER_MODELS_BIND,
    DOCKER_SRC_BIND,
    DOCKER_WORKSPACE,
    IMAGE_EXTENSIONS,
    LIDAR_EXTENSIONS,
    METADATA_REQUIRED_KEYS,
)
from src.misc.io import delete_data_intermediate_dir, load_metadata


PROJECT_ROOT = Path(__file__).resolve().parent


def _get_arguements() -> list[str]:
    parser = argparse.ArgumentParser(description="Auto-label PDB data")

    parser.add_argument(
        "paths_to_data",
        type=str,
        help="Paths to driving session data, separated by a semicolon.",
    )

    args = parser.parse_args()
    PATHS_TO_DATA = (
        os.environ["PATHS_TO_DATA"]
        if "PATHS_TO_DATA" in os.environ
        else args.paths_to_data
    )

    return PATHS_TO_DATA.split(";")


def _verify_data_dirs(data_dir_paths):
    issues = []

    for data_dir_path in data_dir_paths:
        # load metadata
        metadata = load_metadata(data_dir_paths, throw_no_file_error=False)
        if not metadata:
            issues.append(f"[{data_dir_path}] Metadata is empty or invalid JSON.")
            continue

        missing_keys = [key for key in METADATA_REQUIRED_KEYS if key not in metadata]
        if missing_keys:
            issues.append(
                f"[{data_dir_path}] Metadata missing required keys: {missing_keys}"
            )
            continue

        # verify lidar
        lidar_paths = metadata.get("lidar_paths", [])
        if not lidar_paths:
            issues.append(
                f"[{data_dir_path}] Metadata 'lidar_paths' is empty or missing."
            )
        for lidar_path in lidar_paths:
            if not os.path.isdir(lidar_path):
                issues.append(
                    f"[{data_dir_path}] Lidar directory does not exist: {lidar_path}"
                )
                continue

            lidar_files = [
                f
                for f in os.listdir(lidar_path)
                if os.path.splitext(f)[1].lower() in LIDAR_EXTENSIONS
            ]
            if not lidar_files:
                issues.append(
                    f"[{data_dir_path}] No lidar files with extensions {LIDAR_EXTENSIONS} found in {lidar_path}"
                )

        # verify image
        image_paths = metadata.get("image_paths", [])
        if not image_paths:
            issues.append(
                f"[{data_dir_path}] Metadata 'image_paths' is empty or missing."
            )
        for image_path in image_paths:
            if not os.path.isdir(image_path):
                issues.append(
                    f"[{data_dir_path}] Image directory does not exist: {image_path}"
                )
                continue

            image_files = [
                f
                for f in os.listdir(image_path)
                if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
            ]
            if not image_files:
                issues.append(
                    f"[{data_dir_path}] No image files with extensions {IMAGE_EXTENSIONS} found in {image_path}"
                )

        # verify gps
        gps_path = os.path.join(data_dir_path, "gps.csv")
        if not os.path.exists(gps_path):
            issues.append(
                f"[{data_dir_path}] gps.csv not found at expected path: {gps_path}"
            )

        # verify can bus
        canbus_path = os.path.join(data_dir_path, "canbus.json")
        if not os.path.exists(canbus_path):
            issues.append(
                f"[{canbus_path}] gps.csv not found at expected path: {canbus_path}"
            )

    if len(issues) > 0:
        error_log = "Data verification failed:\n" + "\n".join(issues)
        raise Exception(error_log)


def _get_build_configs() -> list[dict]:
    BUILD_CONFIGS = {
        "gps": {
            "dockerfile": "docker/gps.Dockerfile",
            "image_name": "pdb-gps:latest",
        },
        "image": {
            "dockerfile": "docker/image.Dockerfile",
            "image_name": "pdb-image:latest",
        },
        "openpcdet": {
            "dockerfile": "docker/openpcdet.Dockerfile",
            "image_name": "pdb-openpcdet:latest",
        },
        "ab3dmot": {
            "dockerfile": "docker/ab3dmot.Dockerfile",
            "image_name": "pdb-ab3dmot:latest",
        },
    }

    return BUILD_CONFIGS


def _get_execute_configs(data_dir_path) -> list[dict]:
    metadata = load_metadata(data_dir_path)

    # docker containers executed in sequence
    execute_configs = []

    # gps
    execute_configs.append({"name": "gps", "parameters": [data_dir_path]})

    # image
    for image_path in metadata["image_paths"]:
        execute_configs.append(
            {"name": "image", "parameters": [data_dir_path, image_path]}
        )

    # openpcdet -> ab3dmot
    for lidar_path in metadata["lidar_paths"]:
        execute_configs.append(
            {
                "name ": "openpcdet",
                "volumes": {
                    os.path.join(PROJECT_ROOT, "models"): {
                        "bind": DOCKER_MODELS_BIND,
                        "mode": "rw",
                    },
                },
                "parameters": [data_dir_path, lidar_path],
            }
        )

        execute_configs.append(
            {
                "name": "ab3dmot",
                # adding the volume "/workspace/data:/workspace/AB3DMOT/data" might work
            }
        )

    return execute_configs


def _build_image(client, build_config):
    image, build_logs = client.images.build(
        path=".",
        dockerfile=build_config["dockerfile"],
        tag=build_config["image_name"],
        rm=True,
    )

    for chunk in build_logs:
        if "stream" in chunk:
            print(chunk["stream"], end="")
        elif "error" in chunk:
            raise RuntimeError(chunk["error"])


def _create_container_kwargs(execute_config):
    container_kwargs = {
        "image": execute_config["image_name"],
        "volumes": {
            **(execute_config.get("volumes", {})),
            **{
                os.path.join(PROJECT_ROOT, "data"): {
                    "bind": DOCKER_DATA_BIND,
                    "mode": "rw",
                },
                os.path.join(PROJECT_ROOT, "src"): {
                    "bind": DOCKER_SRC_BIND,
                    "mode": "rw",
                },
            },
        },
        "environment": {
            **execute_config.get("environment", {}),
            **{
                "PYTHONPATH": DOCKER_WORKSPACE,
            },
        },
        "remove": True,
        "detach": True,
    }

    if "parameters" in execute_config:
        container_kwargs["command"] = execute_config["parameters"]

    if "gpu" in execute_config and execute_config["gpu"]:
        container_kwargs["device_requests"] = [
            docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])
        ]

    return container_kwargs


def _log_container(container, name: str):
    try:
        for line in container.logs(stream=True):
            print(line.decode(errors="replace"), end="")

        result = container.wait()
        status = result["StatusCode"]

        if status != 0:
            raise RuntimeError(f"{name} failed with exit code {status}")

    finally:
        try:
            container.remove(force=True)
        except Exception:
            pass


def _run_substeps(build_configs: dict, execute_configs: list[dict], dir_i: int = -1):
    client = docker.from_env()

    # delete_data_intermediate_dir()

    # build
    n = len(execute_configs)
    for i, execute_config in enumerate(execute_configs):
        name = execute_config["name"]

        log_header = (
            ">>> main.py " + f"dir:{dir_i if dir_i >= 0 else ''}" + f"step:{i}/{n}"
        )

        print(f"{log_header}: building {name}")
        _build_image(client, build_configs[name])

        # run
        print(f"{log_header}: running {name}")
        container_kwargs = _create_container_kwargs(execute_config)
        container = client.containers.run(**container_kwargs)

        _log_container(container, name)

    # delete_data_intermediate_dir()


if __name__ == "__main__":
    data_dir_paths = _get_arguements()

    _verify_data_dirs(data_dir_paths)

    build_configs = _get_build_configs()

    for dir_i, data_dir_path in enumerate(data_dir_paths):
        execute_configs = _get_execute_configs(data_dir_path)

        _run_substeps(build_configs, execute_configs, dir_i)
