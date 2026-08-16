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
Contains information about the data.

If lidar_rpaths or image_rpaths are not provided, the /lidar and /images directories are recursively searched for paths to directories that contain valid lidar or image files to produce lidar_rpaths or image_rpaths.

Lidar transformation is to allow lidar points to be transformed into optimal position for the detection model.

### Format
{
	"driver_id": str, (required)
	"image_rpaths": [str], (optional)
	"lidar_rpaths": [str], (optional)
	"lidar_transformations": [[float, float, float]] (optional, xyz)
	"gps_rpath": str, (optional)
	"canbus_rpath": str, (optional)
	"heartrate_rpath": str, (optional)
}

# EXECUTION

Run main.py with a single argument: paths to data directories separated by semicolons.

## Permissions
Make sure everything within the PDB_labeller directory is owned by your user.


# Future Development
For the sake of speed, some decisions were hardcoded rather than made adaptable. This documents areas that were hardcoded that may changed.

# Lidar Model
Points are filtered within [-1, 3] meters on the z axis to match PointPillars training.