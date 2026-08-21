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
DOCKER_PLATFORM = "linux/amd64" if platform.system() == "Darwin" else None


def _parse_arguments() -> tuple[list[str], list[str], bool, bool]:
    # set args
    parser = argparse.ArgumentParser(description="Auto-label PDB data")

    parser.add_argument(
        "paths_to_data",
        nargs="*",
        type=str,
        help="Paths to driving session data.",
    )
    parser.add_argument("--build_only", action="store_true", help="Only build images.")

    no_execute_flags = {
        "no_gps": "Do not process GPS data.",
        "no_image": "Do not process camera image data.",
        "no_lidar": "Do not process LiDAR data.",
        "no_openpcdet": "Do not execute openpcdet.",
        "no_ab3dmot": "Do not execute ab3dmot.",
    }

    cleanup_flags = {
        "delete_gps": "Delete GPS related images.",
        "delete_image": "Delete camera image related images.",
        "delete_openpcdet": "Delete OpenPCDet-related images.",
        "delete_ab3dmot": "Delete AB3DMOT-related images.",
        "delete_lidar": "Delete all LiDAR-related images (OpenPCDet and AB3DMOT).",
    }

    rebuild_flags = {
        "rebuild_deps": "Rebuild dependency images even if they already exist.",
        "rebuild_gps": "Rebuild GPS dependency image.",
        "rebuild_image": "Rebuild camera image dependency/image.",
        "rebuild_openpcdet": "Rebuild OpenPCDet-related images.",
        "rebuild_ab3dmot": "Rebuild AB3DMOT-related images.",
        "rebuild_lidar": "Rebuild all LiDAR-related images (OpenPCDet and AB3DMOT).",
    }

    for flag, help_msg in {**no_execute_flags, **cleanup_flags, **rebuild_flags}.items():
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

    no_execute_flags = [flag for flag in no_execute_flags if getattr(args, flag)]
    cleanup_flags = [flag for flag in cleanup_flags if getattr(args, flag)]
    rebuild_flags = [flag for flag in rebuild_flags if getattr(args, flag)]

    return paths_to_data, only_build, no_execute_flags, cleanup_flags, rebuild_flags


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
            "deps": {
                "dockerfile": "docker/gps-deps.Dockerfile",
                "image_name": "pdb-gps-deps:py310-v1",
                "buildargs": {},
            },
            "runner": {
                "dockerfile": "docker/gps.Dockerfile",
                "image_name": "pdb-gps:latest",
                "deps_arg_name": "GPS_DEPS_IMAGE",
            },
        },
        "image": {
            "deps": {
                "dockerfile": "docker/image-deps.Dockerfile",
                "image_name": "pdb-image-deps:py310-v1",
                "buildargs": {},
            },
            "runner": {
                "dockerfile": "docker/image.Dockerfile",
                "image_name": "pdb-image:latest",
                "deps_arg_name": "IMAGE_DEPS_IMAGE",
            },
        },
        "openpcdet": {
            "deps": {
                "dockerfile": "docker/openpcdet-deps.Dockerfile",
                "image_name": "pdb-openpcdet-deps:torch2.7.1-cu128-sm120-pcdet-233f849",
                "buildargs": {
                    "OPENPCDET_COMMIT": "233f849",
                },
            },
            "runner": {
                "dockerfile": "docker/openpcdet.Dockerfile",
                "image_name": "pdb-openpcdet:latest",
                "deps_arg_name": "OPENPCDET_DEPS_IMAGE",
            },
        },
        "ab3dmot": {
            "deps": {
                "dockerfile": "docker/ab3dmot-deps.Dockerfile",
                "image_name": "pdb-ab3dmot-deps:py310-v1",
                "buildargs": {},
            },
            "runner": {
                "dockerfile": "docker/ab3dmot.Dockerfile",
                "image_name": "pdb-ab3dmot:latest",
                "deps_arg_name": "AB3DMOT_DEPS_IMAGE",
            },
        },
    }

    return BUILD_CONFIGS


def _image_exists(image_name: str) -> bool:
    client = docker.from_env()

    try:
        client.images.get(image_name)
        return True
    except docker.errors.ImageNotFound:
        return False


def _build_with_buildx(
    dockerfile: str,
    image_name: str,
    buildargs: dict[str, str] | None = None,
) -> None:
    command = [
        "docker",
        "buildx",
        "build",
        "--load",
        "-f",
        dockerfile,
        "-t",
        image_name,
    ]

    if DOCKER_PLATFORM:
        command.extend(["--platform", DOCKER_PLATFORM])

    for key, value in (buildargs or {}).items():
        command.extend(["--build-arg", f"{key}={value}"])

    command.append(str(PROJECT_ROOT))

    subprocess.run(command, check=True, cwd=PROJECT_ROOT)


def _build_dependency_image(build_config: dict) -> None:
    deps_config = build_config["deps"]

    _build_with_buildx(
        dockerfile=deps_config["dockerfile"],
        image_name=deps_config["image_name"],
        buildargs=deps_config.get("buildargs"),
    )


def _build_runner_image(build_config: dict) -> None:
    deps_config = build_config["deps"]
    runner_config = build_config["runner"]

    buildargs = {
        "HOST_UID": str(os.getuid()),
        "HOST_GID": str(os.getgid()),
        runner_config["deps_arg_name"]: deps_config["image_name"],
    }

    _build_with_buildx(
        dockerfile=runner_config["dockerfile"],
        image_name=runner_config["image_name"],
        buildargs=buildargs,
    )


def _ensure_service_image(
    name: str,
    build_config: dict,
    rebuild_flags: list,
    built_runners: set[str],
) -> None:
    deps_image = build_config["deps"]["image_name"]

    rebuild_requested = 'rebuild_deps' in rebuild_flags or f'rebuild_{name}' in rebuild_flags
    if rebuild_requested or not _image_exists(deps_image):
        print(f">>> building dependency image: {name}", flush=True)
        _build_dependency_image(build_config)
    else:
        print(f">>> dependency image exists: {deps_image}", flush=True)

    if name not in built_runners:
        print(f">>> building runner image: {name}", flush=True)
        _build_runner_image(build_config)
        built_runners.add(name)


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
                execute_configs.append(
                    {
                        "name": "openpcdet",
                        "gpu": True,
                        "parameters": [container_data_dir_path, str(i)],
                        "volumes": {os.path.join(PROJECT_ROOT, "models"): {"bind": "/workspace/models", "mode": "ro"}},
                    }
                )

            if "no_ab3dmot" not in no_execute_flags:
                execute_configs.append(
                    {
                        "name": "ab3dmot",
                        "parameters": [str(i)],
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
        "image": build_config["runner"]["image_name"],
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


def _run_docker_cleanup(cleanup_flags: list[str], apply=True) -> None:
    cleanup_script = PROJECT_ROOT / "tools" / "docker_cleanup.sh"
    if apply:
        subprocess.run(["bash", str(cleanup_script), "--apply", *cleanup_flags], check=False)
    else:
        subprocess.run(["bash", str(cleanup_script), *cleanup_flags], check=False)


def _run_substeps(
    build_configs: dict,
    execute_configs: list[dict],
    built_runners: set[str],
    rebuild_flags: list,
    dir_i: int = -1,
):
    delete_data_intermediate_dir()

    # build & run
    n = len(execute_configs)
    for i in range(n):
        execute_config = execute_configs[i]
        name = execute_config["name"]
        build_config = build_configs[name]

        log_header = ">>> main.py " + (f"dir:{dir_i} " if dir_i >= 0 else "") + f"step:{i + 1}/{n}"

        _ensure_service_image(
            name=name,
            build_config=build_config,
            rebuild_flags=rebuild_flags,
            built_runners=built_runners,
        )

        # run
        print(f"{log_header} % running {name}", flush=True)
        _run_container(name, execute_config, build_config)

    # delete_data_intermediate_dir() # TODO: Add back inn


def _build_requested_images(
    build_configs: dict,
    no_execute_flags: list[str],
    rebuild_flags: list,
) -> None:
    built_runners: set[str] = set()

    for name, build_config in build_configs.items():
        no_gps = name == "gps" and "no_gps" in no_execute_flags
        no_image = name == "image" and "no_image" in no_execute_flags
        no_lidar = name in ["openpcdet", "ab3dmot"] and "no_lidar" in no_execute_flags

        if not (no_gps or no_image or no_lidar):
            _ensure_service_image(
                name=name,
                build_config=build_config,
                rebuild_flags=rebuild_flags,
                built_runners=built_runners,
            )


def main():
    data_dir_paths, only_build, no_execute_flags, cleanup_flags, rebuild_flags = _parse_arguments()

    _run_docker_cleanup(cleanup_flags, apply=False)

    try:
        verify_data_dirs(data_dir_paths)

        build_configs = _get_build_configs()

        if only_build:
            _build_requested_images(
                build_configs=build_configs,
                no_execute_flags=no_execute_flags,
                rebuild_flags=rebuild_flags,
            )
        else:
            built_runners: set[str] = set()

            # execute and build images on demand
            for dir_i, data_dir_path in enumerate(data_dir_paths):
                execute_configs = _get_execute_configs(data_dir_path, no_execute_flags)

                _run_substeps(
                    build_configs=build_configs,
                    execute_configs=execute_configs,
                    built_runners=built_runners,
                    rebuild_flags=rebuild_flags,
                    dir_i=dir_i,
                )
    finally:
        _run_docker_cleanup(cleanup_flags, apply=False)


if __name__ == "__main__":
    main()
