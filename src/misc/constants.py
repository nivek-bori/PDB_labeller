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

# The AB3DMOT detection_results dataset uses the same class IDs as
# OpenPCDet: Car=1, Pedestrian=2, Cyclist=3.
OPENPCDET_TO_AB3DMOT = {
    1: 1,
    2: 2,
    3: 3,
}

AB3DMOT_ID_TO_NAME = {
    1: "Car",
    2: "Pedestrian",
    3: "Cyclist",
}

KITTI_CLASS_ID_TO_NAME = ["Car", "Pedestrian", "Cyclist"]

IMAGE_OUTPUT_FORMAT = "parquet"

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

IMAGE_OUTPUT_FORMAT = ".parquet"

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

POINTPILLARS_POINT_CLOUD_RANGE = [
    0.0,
    -39.68,
    -3.0,
    69.12,
    39.68,
    1.0,
]

# Time
NS_PER_SECOND = 1_000_000_000
NS_TIMESTAMP_THRESHOLD = 1e14
GPS_UNIX_EPOCH_OFFSET_SECONDS = 315964800 - 18 # 18 leap seconds

# Docker
DOCKER_WORKSPACE = "/workspace"
DOCKER_DATA_BIND = f"{DOCKER_WORKSPACE}/data"
DOCKER_SRC_BIND = f"{DOCKER_WORKSPACE}/src"
DOCKER_MODELS_BIND = f"{DOCKER_WORKSPACE}/models"

# Data
METADATA_REQUIRED_KEYS = ["driver_id"]
METADATA_DEFAULTS = {
    "unique_name": None,
    "image_rpaths": None,
    "lidar_rpaths": None,
    "lidar_transformations": None,
    "gps_rpath": "gps.csv",
    "canbus_rpath": "canbus.json",
    "heartrate_rpath": "heartrate.csv",
    "sampling_hertz": 5,
}
