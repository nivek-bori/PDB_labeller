# Dependencies
No python dependencies. Download pointpillars.pth into models. Here is a link: https://drive.google.com/file/d/1wMxWTpU1qUoY3DsCH31WJmvJxcjFXKlm/view

# Input Data Format

## Default Data Directory Format:

/data_dir
	/lidar
		/recursive/recursive/...
			nanoseconds.bin
			nanoseconds.bin
			nanoseconds.bin
			nanoseconds.bin
	/images
		/recursive/recursive/...
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

If lidar_rpaths or image_rpaths are not provided, the /lidar and /images directories are recursively searched for paths to directories th 

Lidar transformation is to allow lidar points to be transformed into optimal position for the detection model.

### Metadata.json Format
{
	"driver_id": str, (required)
	"unique_name": str, (optional)
	"image_rpaths": [str], (optional)
	"lidar_rpaths": [str], (optional)
	"lidar_transformations": [[float, float, float]] (optional, xyz)
	"gps_rpath": str, (optional)
	"canbus_rpath": str, (optional)
	"heartrate_rpath": str, (optional)
}


# Output



# Execution
Run ```main.py``` with each path to a data directories as an argument. Flags modify execution.

## Permissions
Make sure everything within the PDB_labeller directory is owned by your user.


# Future Development
For the sake of speed, some decisions were hardcoded rather than made adaptable. This documents areas that were hardcoded that may changed.

## Lidar Model
Points are filtered within [-1, 3] meters on the z axis to match PointPillars training.