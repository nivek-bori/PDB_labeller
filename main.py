import docker

client = docker.from_env()

client.containers.run(
    image="TODO",
    command="TODO",
    volumes={
        "/host/TODO": {"bind": "/workspace/data/TODO", "mode": "rw"},
        "/host/output": {"bind": "/workspace/output", "mode": "rw"},
    },
    device_requests=[docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])],
    remove=True,
)