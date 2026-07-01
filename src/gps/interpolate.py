import numpy as np
from filterpy.kalman import KalmanFilter
import os
import pandas as pd
from pandas import DataFrame
from src.misc.io import get_full_path, safe_makedirs
import csv
from typing import Union


EARTH_RADIUS_M = 6378137.0
GPS_STD = 0.1  # decimeter-level GNSS accuracy; TODO: make a parameter


def load_gps_dataframe(gps_file_path: str) -> DataFrame:
	gps_file_path = get_full_path(gps_file_path)

	try:
		gps_dataframe = pd.read_csv(
			gps_file_path,
			skiprows=7,
			skipinitialspace=True,
			dtype={
				"Time (GPS ns)": "int64",
			},
		)
	except Exception as e:
		raise RuntimeError(f"Failed to load GPS data from '{gps_file_path}': {e}")

	return gps_dataframe


def write_txyz_csv(txyz_csv: list[list[Union[str, float, int]]]):
	write_path = "data/intermediate/gps.csv"
	safe_makedirs(write_path)

	with open(write_path, "w", newline="") as f:
		writer = csv.writer(f)
		writer.writerows(txyz_csv)


def convert_lnglat_to_meters(gps_dataframe: DataFrame):
    timestamps = gps_dataframe["Time (GPS ns)"]
    z = gps_dataframe["Altitude (in)"]

    lat_0 = gps_dataframe.iloc[0]["Latitude (deg)"]
    lng_0 = gps_dataframe.iloc[0]["Longitude (deg)"]

    lats = gps_dataframe["Latitude (deg)"].values
    longs = gps_dataframe["Longitude (deg)"].values

    relative_x = (
        (np.deg2rad(longs) - np.deg2rad(lng_0))
        * EARTH_RADIUS_M
        * np.cos(np.deg2rad(lat_0))
    )
    relative_y = (np.deg2rad(lats) - np.deg2rad(lat_0)) * EARTH_RADIUS_M

    return list(zip(timestamps, relative_x, relative_y, z))


# in meters
def initialize_kalman_filter(initial_x: float, initial_y: float, initial_z: float) -> KalmanFilter:
    KF = KalmanFilter(dim_x=6, dim_z=3)

    # x, y, vx, vy
    KF.x = np.array([[initial_x], [initial_y], [initial_z], [0], [0], [0]], dtype=float)

    KF.H = np.array(
        [
            [1, 0, 0, 0, 0, 0],  # get x
            [0, 1, 0, 0, 0, 0],  # get y
            [0, 0, 1, 0, 0, 0],  # get z
        ],
        dtype=float,
    )

    # uncertainty matrix
    KF.P = np.diag(
        [
            10.0,  # x uncertainty
            10.0,  # y uncertainty
            10.0,  # y uncertainty
            25.0,  # vx uncertainty
            25.0,  # vy uncertainty
            25.0,  # vy uncertainty
        ]
    )

    KF.R = np.diag([GPS_STD**2, GPS_STD**2, GPS_STD**2])

    return KF


def update_kalman_filter_matrices(KF: KalmanFilter, dt: int) -> KalmanFilter:
	from filterpy.common import Q_discrete_white_noise

	# state order: [x, y, z, vx, vy, vz]
	KF.F = np.array(
		[
			[1, 0, 0, dt, 0, 0],
			[0, 1, 0, 0, dt, 0],
			[0, 0, 1, 0, 0, dt],
			[0, 0, 0, 1, 0, 0],
			[0, 0, 0, 0, 1, 0],
			[0, 0, 0, 0, 0, 1],
		],
		dtype=float,
	)

	accel_std = 2.0

	KF.Q = Q_discrete_white_noise(
		dim=2,
		dt=dt,
		var=accel_std**2,
		block_size=3,
		order_by_dim=False,
	)

	return KF


def main(gps_file_path: str):
    # load & format data
    gps_dataframe = load_gps_dataframe(gps_file_path)
    txyz_dataset = convert_lnglat_to_meters(gps_dataframe)

    # flagpost
    prev_timestamp = int(txyz_dataset[0][0])
    initial_x = float(txyz_dataset[0][1])
    initial_y = float(txyz_dataset[0][2])
    initial_z = float(txyz_dataset[0][3])

    KF = initialize_kalman_filter(initial_x, initial_y, initial_z)

    # output data
    txyz_csv = [
        ["timestamp", "relative_x", "relative_y", "z"],
        [prev_timestamp, initial_x, initial_y, initial_z],
    ]

    for timestamp, x, y, z in txyz_dataset[1:]:
        dt = (timestamp - prev_timestamp) / 1e9  # convert ns to s
        KF = update_kalman_filter_matrices(KF, dt)

        KF.predict()
        KF.update(np.array([[float(x)], [float(y)], [float(z)]]))

        txyz_csv.append([int(timestamp), KF.x[0, 0], KF.x[1, 0], KF.x[2, 0]])

        prev_timestamp = timestamp

    write_txyz_csv(txyz_csv)


if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(
		description="Convert lat and long to local x and y (in meters) and apply Kalman Filter"
	)
	parser.add_argument(
		"gps_file_path",
		type=str,
		help="Path to the csv file containing the gps data.",
	)
	args = parser.parse_args()

	if "GPS_FILE_PATH" in os.environ:
		main(os.environ["GPS_FILE_PATH"])
	else:
		main(args.gps_file_path)
