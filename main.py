import os
import docker
import argparse
import platform
import subprocess

from pathlib import Path
from src.misc.constants import (
    DOCKER_DATA_BIND,
    DOCKER_MODELS_BIND,
    DOCKER_SRC_BIND,
    DOCKER_WORKSPACE,
)
from src.misc.io import delete_data_intermediate_dir, load_metadata, verify_data_dirs


PROJECT_ROOT = Path(__file__).resolve().parent
BUILT_IMAGES = []
DOCKER_PLATFORM = "linux/amd64" if platform.system() == "Darwin" else None


def _parse_arguments() -> tuple[list[str], list[str], bool]:
    # set args
    parser = argparse.ArgumentParser(description="Auto-label PDB data")

    parser.add_argument(
        "paths_to_data",
        nargs="*",
        type=str,
        help="Paths to driving session data.",
    )
    parser.add_argument("--build_only", action="store_true", help="Only build images.")

    arg_flags = {
        "no_gps": "Do not process GPS data.",
        "no_image": "Do not process camera image data.",
        "no_lidar": "Do not process LiDAR data.",
        "no_openpcdet": "Do not execute openpcdet.",
        "no_ab3dmot": "Do not execute ab3dmot.",
    }

    for flag, help_msg in arg_flags.items():
        parser.add_argument(
            f"--{flag}",
            action="store_true",
            help=help_msg,
        )
   
    # parse args
    args = parser.parse_args()

    paths_to_data = os.environ.get("PATHS_TO_DATA", args.paths_to_data)
    only_build = args.build_only
    if only_build:  # no need for paths
        paths_to_data = []
    elif not paths_to_data:
        parser.error("paths_to_data must be provided either as a command-line argument or through the PATHS_TO_DATA environment variable.")

    flags = [flag for flag in arg_flags if getattr(args, flag)]

    return paths_to_data, flags, only_build


def _to_container_data_path(host_path: str | Path) -> str:
    host_data_root = (PROJECT_ROOT / "data").resolve()
    resolved_path = Path(host_path).resolve()

    try:
        relative_path = resolved_path.relative_to(host_data_root)
    except ValueError as exc:
        raise ValueError(f"Path must be inside {host_data_root}: {resolved_path}") from exc

    return str(Path(DOCKER_DATA_BIND) / relative_path)


def _get_build_configs() -> dict[str, dict]:
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


def _build_image(build_config):
    client = docker.from_env()

    build_kwargs = {
        "path": str(PROJECT_ROOT),
        "dockerfile": build_config["dockerfile"],
        "tag": build_config["image_name"],
        "rm": True,
        "forcerm": True,
        "decode": True,
        "buildargs": {
            "HOST_UID": str(os.getuid()),
            "HOST_GID": str(os.getgid()),
        },
    }

    if DOCKER_PLATFORM:
        build_kwargs["platform"] = DOCKER_PLATFORM

    build_logs = client.api.build(**build_kwargs)

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
        for i in range(len(metadata["image_rpaths"])):
            execute_configs.append(
                {
                    "name": "image",
                    "parameters": [container_data_dir_path, str(i)],
                    "volumes": {
                        os.path.join(PROJECT_ROOT, "models"): {
                            "bind": "/workspace/models",
                            "mode": "rw",
                        },
                    },
                }
            )

    # openpcdet -> ab3dmot
    if "no_lidar" not in no_execute_flags:
        for i in range(len(metadata["lidar_rpaths"])):
            if "no_openpcdet" not in no_execute_flags:
                execute_configs.append({"name": "openpcdet", "gpu": True, "parameters": [container_data_dir_path, str(i)]})

            if "no_ab3dmot" not in no_execute_flags:
                execute_configs.append(
                    {
                        "name": "ab3dmot",
                        "parameters": [container_data_dir_path, str(i)],
                        "volumes": {
                            # TOOD: remove (currently only for development purposes)
                            os.path.join(PROJECT_ROOT.parent, "AB3DMOT"): {
                                "bind": "/workspace/AB3DMOT",
                                "mode": "rw",
                            },
                        },
                    }
                )

    return execute_configs


def _create_run_container_kwargs(execute_config, build_config):
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
        "environment": {**execute_config.get("environment", {})},
        "remove": False,
        "detach": True,
        "user": f"{os.getuid()}:{os.getgid()}",
    }

    if "parameters" in execute_config:
        container_kwargs["command"] = execute_config["parameters"]

    if execute_config.get("gpu"):
        container_kwargs["device_requests"] = [docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])]

    if DOCKER_PLATFORM:
        container_kwargs["platform"] = DOCKER_PLATFORM

    return container_kwargs


def _run_container(name: str, execute_config, build_config) -> None:
    container_kwargs = _create_run_container_kwargs(execute_config, build_config)

    client = docker.from_env()
    container = client.containers.run(**container_kwargs)

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


def _run_docker_cleanup(apply=True) -> None:
    cleanup_script = PROJECT_ROOT / "tools" / "docker_cleanup.sh"
    if apply:
        subprocess.run(["bash", str(cleanup_script), "--apply"], check=False)
    else:
        subprocess.run(["bash", str(cleanup_script)], check=False)


def _run_substeps(build_configs: dict, execute_configs: list[dict], dir_i: int = -1):
    delete_data_intermediate_dir()

    BUILT_IMAGES = []

    # build
    n = len(execute_configs)
    for i in range(n):
        execute_config = execute_configs[i]
        name = execute_config["name"]
        build_config = build_configs[name]

        log_header = ">>> main.py " + (f"dir:{dir_i} " if dir_i >= 0 else "") + f"step:{i + 1}/{n}"

        # build
        if name in BUILT_IMAGES:
            print(f"{log_header} % image already built: {name}", flush=True)
        else:
            print(f"{log_header} % building {name}", flush=True)
            _build_image(build_config)
            BUILT_IMAGES.append(name)

        # run
        print(f"{log_header} % running {name}", flush=True)
        _run_container(name, execute_config, build_config)

    # delete_data_intermediate_dir() # TODO: Add back inn


def main():
    try:
        data_dir_paths, no_execute_flags, only_build = _parse_arguments()
        if DOCKER_PLATFORM:
            print(f">>> macOS detected: using Docker platform {DOCKER_PLATFORM}", flush=True)

        verify_data_dirs(data_dir_paths)

        build_configs = _get_build_configs()

        if only_build:
            for name in build_configs:
                no_gps = name == "gps" and "no_gps" in no_execute_flags
                no_image = name == "image" and "no_image" in no_execute_flags
                no_lidar = name in ["openpcdet", "ab3dmot"] and "no_lidar" in no_execute_flags

                if not (no_gps or no_image or no_lidar):
                    _build_image(build_configs[name])
        else:
            # execute and build images on demand
            for dir_i, data_dir_path in enumerate(data_dir_paths):
                execute_configs = _get_execute_configs(data_dir_path, no_execute_flags)

                _run_substeps(build_configs, execute_configs, dir_i)
    finally:
        _run_docker_cleanup(apply=False)


if __name__ == "__main__":
    main()
