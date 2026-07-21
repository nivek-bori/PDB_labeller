import os
from pathlib import Path
import docker
import argparse

from src.misc.constants import (
    DOCKER_DATA_BIND,
    DOCKER_MODELS_BIND,
    DOCKER_SRC_BIND,
    DOCKER_WORKSPACE,
)
from src.misc.io import delete_data_intermediate_dir, load_metadata, verify_data_dirs


PROJECT_ROOT = Path(__file__).resolve().parent
BUILT_IMAGES = []


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-label PDB data")

    parser.add_argument(
        "paths_to_data",
        nargs="?",
        type=str,
        help="Paths to driving session data, separated by a semicolon.",
    )

    parser.add_argument(
        "--no_gps",
        action="store_true",
        help="Do not process GPS data.",
    )

    parser.add_argument(
        "--no_image",
        action="store_true",
        help="Do not process camera image data.",
    )

    parser.add_argument(
        "--no_lidar",
        action="store_true",
        help="Do not process LiDAR data.",
    )

    args = parser.parse_args()

    paths_string = os.environ.get("PATHS_TO_DATA", args.paths_to_data)
    if not paths_string:
        parser.error("paths_to_data must be provided either as a command-line argument or through the PATHS_TO_DATA environment variable.")

    paths_to_data = [path.strip() for path in paths_string.split(";") if path.strip()]
    flags = [flag for flag in ["no_gps", "no_image", "no_lidar"] if getattr(args, flag)]

    return paths_to_data, flags


def _to_container_data_path(host_path: str | Path) -> str:
    host_data_root = (PROJECT_ROOT / "data").resolve()
    resolved_path = Path(host_path).resolve()

    try:
        relative_path = resolved_path.relative_to(host_data_root)
    except ValueError as exc:
        raise ValueError(
            f"Path must be inside {host_data_root}: {resolved_path}"
        ) from exc

    return str(Path(DOCKER_DATA_BIND) / relative_path)


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


def _get_execute_configs(data_dir_path: str, no_execute_flags: list[str]) -> list[dict]:
    metadata = load_metadata(data_dir_path)
    container_data_dir_path = _to_container_data_path(data_dir_path)

    # docker containers executed in sequence
    execute_configs = []

    # gps
    if "no_gps" not in no_execute_flags:
        execute_configs.append({"name": "gps", "parameters": [container_data_dir_path]})

    # image
    if "no_image" not in no_execute_flags:
        for image_rpath in metadata["image_rpaths"]:
            execute_configs.append({"name": "image", "parameters": [container_data_dir_path, image_rpath]})

    # openpcdet -> ab3dmot
    if "no_lidar" not in no_execute_flags:
        for lidar_rpath in metadata["lidar_rpaths"]:
            execute_configs.append(
                {
                    "name": "openpcdet",
                    "gpu": True,
                    "volumes": {
                        os.path.join(PROJECT_ROOT, "models"): {
                            "bind": DOCKER_MODELS_BIND,
                            "mode": "rw",
                        },
                    },
                    "parameters": [container_data_dir_path, lidar_rpath],
                }
            )

            # TODO: Add in when code done
            # execute_configs.append(
            #     {
            #         "name": "ab3dmot",
            #         # adding the volume "/workspace/data:/workspace/AB3DMOT/data" might work
            #     }
            # )

            # TODO: Add in when code done
            # execute_configs.append(
            #     {
            #         "name": "sequencer",
            #         # todo
            #     }
            # )

    return execute_configs


def _build_image(client, build_config):
    build_logs = client.api.build(
        path=str(PROJECT_ROOT),
        dockerfile=build_config["dockerfile"],
        tag=build_config["image_name"],
        rm=True,
        decode=True,
    )

    image_id = None

    for chunk in build_logs:
        if "stream" in chunk:
            print(chunk["stream"], end="", flush=True)

        if "status" in chunk:
            progress = chunk.get("progress", "")
            print(
                f"{chunk['status']} {progress}",
                flush=True,
            )

        if "aux" in chunk:
            image_id = chunk["aux"].get("ID", image_id)

        if "error" in chunk:
            raise RuntimeError(chunk["error"])

        if "errorDetail" in chunk:
            message = chunk["errorDetail"].get(
                "message",
                str(chunk["errorDetail"]),
            )
            raise RuntimeError(message)

    try:
        return client.images.get(build_config["image_name"])
    except docker.errors.ImageNotFound as exc:
        raise RuntimeError(f"Build completed but image {build_config['image_name']} was not found") from exc


def _create_container_kwargs(execute_config, build_config):
    container_kwargs = {
        "image": build_config["image_name"],
        "volumes": {
            **(execute_config.get("volumes", {})),
            os.path.join(PROJECT_ROOT, "data"): {
                "bind": DOCKER_DATA_BIND,
                "mode": "rw",
            },
            os.path.join(PROJECT_ROOT, "src"): {
                "bind": DOCKER_SRC_BIND,
                "mode": "rw",
            },
        },
        "environment": {
            **execute_config.get("environment", {}),
            "PYTHONPATH": DOCKER_WORKSPACE,
            "PYTHONUNBUFFERED": "1",
        },
        "remove": False,
        "detach": True
    }

    if "parameters" in execute_config:
        container_kwargs["command"] = execute_config["parameters"]

    if "gpu" in execute_config and execute_config["gpu"]:
        container_kwargs["device_requests"] = [docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])]

    return container_kwargs


def _log_container(container, name: str) -> None:
    try:
        for raw_line in container.logs(
            stream=True,
            follow=True,
            stdout=True,
            stderr=True,
        ):
            line = raw_line.decode("utf-8", errors="replace")
            print(f"[{name}] {line}", end="", flush=True)

        result = container.wait()
        status = result["StatusCode"]

        if status != 0:
            raise RuntimeError(f"{name} failed with exit code {status}")

    finally:
        try:
            container.remove(force=True)
        except docker.errors.NotFound:
            pass
        except docker.errors.APIError as exc:
            # Do not let a cleanup problem hide the real container error.
            print(f"[{name}] Warning: failed to remove container: {exc}", flush=True)


def _run_substeps(build_configs: dict, execute_configs: list[dict], dir_i: int = -1):
    client = docker.from_env()

    delete_data_intermediate_dir()

    # build
    n = len(execute_configs)
    for i, execute_config in enumerate(execute_configs, start=1):
        name = execute_config["name"]
        build_config = build_configs[name]

        log_header = ">>> main.py " + (f"dir:{dir_i} " if dir_i >= 0 else "") + f"step:{i}/{n}"

        # build if not built
        if name not in BUILT_IMAGES:
            print(f"{log_header} % building {name}", flush=True)
            _build_image(client, build_config)

            BUILT_IMAGES.append(name)

        # run
        print(f"{log_header} % running {name}", flush=True)
        container_kwargs = _create_container_kwargs(execute_config, build_config)
        container = client.containers.run(**container_kwargs)

        _log_container(container, name)

    # delete_data_intermediate_dir() # TODO: Add back inn


if __name__ == "__main__":
    data_dir_paths, no_execute_flags = _parse_arguments()

    verify_data_dirs(data_dir_paths)

    build_configs = _get_build_configs()

    for dir_i, data_dir_path in enumerate(data_dir_paths):
        execute_configs = _get_execute_configs(data_dir_path, no_execute_flags)

        _run_substeps(build_configs, execute_configs, dir_i)
