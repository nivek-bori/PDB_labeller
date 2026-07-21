# DATA

## Default Data Directory Format:

/data_dir
	/lidar
		/recursive
			nanoseconds.bin
			nanoseconds.bin
			nanoseconds.bin
			nanoseconds.bin
	/images
		/recursive
			nanoseconds.IMAGE_EXTENSION
			nanoseconds.IMAGE_EXTENSION
			nanoseconds.IMAGE_EXTENSION
			nanoseconds.IMAGE_EXTENSION
	metadata.json
	gps.csv
	canbux.json
	heartrate.csv

## Metadata.json
Only the metadata.json is requried to be in data_dir. The rest of the paths can be changed from the default by specificing in metadata.json.

If lidar_paths or image_paths are not provided, the /lidar and /images directories are recursively searched for paths to directories that contain valid lidar or image files to produce lidar_paths or image_paths.

### Format
{
	"driver_id": str, (required)
	"lidar_paths": [str], (optional)
	"image_paths": [str], (optional)
	"gps_rpath": str, (optional)
	"canbus_rpath": str, (optional)
	"heartrate_rpath": str, (optional)
}

# EXECUTION

Run main.py with a single argument: paths to data directories separated by semicolons. 