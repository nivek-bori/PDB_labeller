# Class mappings
YOLO_TO_PDB = {
    "car": "Vehicle",
    "truck": "Vehicle",
    "bus": "Vehicle",
    "motorcycle": "Vehicle",
    "person": "Pedestrian",
    "bicycle": "Cyclist",
}

PDB_TO_KITTI = {
    "Vehicle": "Car",
    "Pedestrian": "Pedestrian",
    "Cyclist": "Cyclist",
}

 = {
    "Vehicle": 1,
    "Car": 1,
    "Pedestrian": 2,
    "Cyclist": 3,
}

IMAGE_COLUMNS = [
    "camera_name",
    # TODO: add driver_id
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

LIDAR_EXTENSIONS = [".bin"]

# YOLO
YOLO_MODEL_PATH = "models/yolo26l.pt"
YOLO_TRACKER = "botsort.yaml"

# GPS
EARTH_RADIUS_M = 6378137.0
GPS_STD = 1.27 # meters
GPS_CSV_SKIP_ROWS = 7
RAW_GPS_COL_TIME = "Time (GPS ns)"
RAW_GPS_COL_ALTITUDE = "Altitude (in)"
RAW_GPS_COL_LATITUDE = "Latitude (deg)"
RAW_GPS_COL_LONGITUDE = "Longitude (deg)"
RAW_GPS_COL_VELOCITY_FORWARD = "Velocity forward (mph)"
RAW_GPS_COL_VELOCITY_LATERAL = "Velocity lateral (mph)"
RAW_GPS_COL_ACCELERATION_FORWARD = "Acceleration forward (m/s²)"
RAW_GPS_COL_ACCELERATION_LATERAL = "Acceleration lateral (m/s²)"

# Oxts
OXTS_DEFAULT_VALUES = {
    "lat": 0.0,
    "lon": 0.0,
    "alt": 0.0,
    "roll": 0.0,
    "pitch": 0.0,
    "yaw": 0.0,
    "vn": 0.0,
    "ve": 0.0,
    "vf": 0.0,
    "vl": 0.0,
    "vu": 0.0,
    "ax": 0.0,
    "ay": 0.0,
    "az": 0.0,
    "af": 0.0,
    "al": 0.0,
    "au": 0.0,
    "wx": 0.0,
    "wy": 0.0,
    "wz": 0.0,
    "wf": 0.0,
    "wl": 0.0,
    "wu": 0.0,
    "pos_accuracy": 1.5,
    "vel_accuracy": 0.05,
    "navstat": 0,
    "numsats": 0,
    "posmode": 0,
    "velmode": 0,
    "orimode": 0,
}

# Lidar preprocessing
LIDAR_RANGE_PERCENTILES = (0.1, 99.9)
LIDAR_POINT_DIM = 4

# Time
NS_PER_SECOND = 1_000_000_000
NS_TIMESTAMP_THRESHOLD = 1e14

# Docker
DOCKER_WORKSPACE = "/workspace"
DOCKER_DATA_BIND = f"{DOCKER_WORKSPACE}/data"
DOCKER_SRC_BIND = f"{DOCKER_WORKSPACE}/src"
DOCKER_MODELS_BIND = f"{DOCKER_WORKSPACE}/models"

# Data
METADATA_REQUIRED_KEYS = ["lidar_paths", "image_paths", "driver_id"]