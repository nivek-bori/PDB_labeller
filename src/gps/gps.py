import numpy as np
from filterpy.kalman import KalmanFilter
import os
import pandas as pd
from pandas import DataFrame
from src.misc.constants import (
	EARTH_RADIUS_M,
	OXTS_DEFAULT_VALUES,
	RAW_GPS_COL_ACCELERATION_FORWARD,
	RAW_GPS_COL_ACCELERATION_LATERAL,
	RAW_GPS_COL_ALTITUDE,
	RAW_GPS_COL_LATITUDE,
	RAW_GPS_COL_LONGITUDE,
	RAW_GPS_COL_TIME,
	RAW_GPS_COL_VELOCITY_FORWARD,
	RAW_GPS_COL_VELOCITY_LATERAL,
	GPS_CSV_SKIP_ROWS,
	GPS_STD,
	NS_PER_SECOND,
)
from src.misc.io import safe_makedirs
import csv
from typing import Union


def _load_gps_dataframe(gps_file_path: str) -> DataFrame:
	try:
		gps_dataframe = pd.read_csv(
			gps_file_path,
			skiprows=GPS_CSV_SKIP_ROWS,
			skipinitialspace=True,
			dtype={
				RAW_GPS_COL_TIME: "int64",
			},
		)
	except Exception as e:
		raise RuntimeError(f"Failed to load GPS data from '{gps_file_path}': {e}")

	return gps_dataframe


def _format_gpd_dataframe(gps_dataframe: DataFrame):
	def format_xyz(lats: list[float], lons: list[float], alt: list[float]):
		lats, lons, alt = np.array(lats), np.array(lons), np.array(alt)

		lat_0, lon_0 = lats[0], lons[0]

		x_meters = (
			(np.deg2rad(lons) - np.deg2rad(lon_0))
			* EARTH_RADIUS_M
			* np.cos(np.deg2rad(lat_0))
		)
		y_meters = (np.deg2rad(lats) - np.deg2rad(lat_0)) * EARTH_RADIUS_M
		z_meters = alt * 0.0254

		return x_meters, y_meters, z_meters

	def format_derivatives(x_meters: list, y_meters: list, z_meters: list):
		def calculate_derivative(arr: list):
			return [0] + [arr[i] - arr[i - 1] for i in range(1, len(arr))]

		ve = calculate_derivative(x_meters)
		vn = calculate_derivative(y_meters)
		vu = calculate_derivative(z_meters)
		au = calculate_derivative(vu)

		vf, vl, af, al = None, None, None, None

		if (gps_dataframe[RAW_GPS_COL_VELOCITY_FORWARD] != 0).any():
			vf = gps_dataframe[RAW_GPS_COL_VELOCITY_FORWARD] * 0.44704

		if (gps_dataframe[RAW_GPS_COL_VELOCITY_LATERAL] != 0).any():
			vl = gps_dataframe[RAW_GPS_COL_VELOCITY_LATERAL] * 0.44704

		if (gps_dataframe[RAW_GPS_COL_ACCELERATION_FORWARD] != 0).any():
			af = gps_dataframe[RAW_GPS_COL_ACCELERATION_FORWARD]

		if (gps_dataframe[RAW_GPS_COL_ACCELERATION_LATERAL] != 0).any():
			al = gps_dataframe[RAW_GPS_COL_ACCELERATION_LATERAL]

		au = calculate_derivative(vu)

		return ve, vn, vf, vl, vu, af, al, au

	x_meters, y_meters, z_meters = format_xyz(
		gps_dataframe[RAW_GPS_COL_LATITUDE],
		gps_dataframe[RAW_GPS_COL_LONGITUDE],
		gps_dataframe[RAW_GPS_COL_ALTITUDE],
	)
	ve, vn, vf, vl, vu, af, al, au = format_derivatives(x_meters, y_meters, z_meters)

	return {
		"timestamp": gps_dataframe[RAW_GPS_COL_TIME],
		"lat": gps_dataframe[RAW_GPS_COL_LATITUDE],
		"lon": gps_dataframe[RAW_GPS_COL_LONGITUDE],
		"x": x_meters,
		"y": y_meters,
		"z": z_meters,
		"ve": ve,
		"vn": vn,
		"vf": vf,
		"vl": vl,
		"vu": vu,
		"af": af,
		"al": al,
		"au": au,
	}


# in meters
def _initialize_kalman_filter(
	initial_x: float, initial_y: float, initial_z: float
) -> KalmanFilter:
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
			25.0,  # vz uncertainty
		]
	)

	KF.R = np.diag([GPS_STD**2, GPS_STD**2, GPS_STD**2])

	return KF


def _update_kalman_filter_matrices(KF: KalmanFilter, dt: int) -> KalmanFilter:
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


def _apply_kalman_filter(gps_dataset: dict[str, list]) -> dict[str, list]:
	timestamps, x, y, z = (
		gps_dataset["timestamp"],
		gps_dataset["x"],
		gps_dataset["y"],
		gps_dataset["z"],
	)

	new_x, new_y, new_z = [], [], []

	# initial flagpost
	prev_timestamp, initial_x, initial_y, initial_z = (
		int(timestamps[0]),
		float(x[0]),
		float(y[0]),
		float(z[0]),
	)

	# apply KF
	KF = _initialize_kalman_filter(initial_x, initial_y, initial_z)
	for i in range(min(map(len, [timestamps, x, y, z]))):
		timestamp = timestamps[i]

		dt = (timestamp - prev_timestamp) / NS_PER_SECOND
		KF = _update_kalman_filter_matrices(KF, dt)

		KF.predict()
		KF.update(np.array([[float(x[i])], [float(y[i])], [float(z[i])]]))

		new_x.append(KF.x[0, 0])
		new_y.append(KF.x[1, 0])
		new_z.append(KF.x[2, 0])

		prev_timestamp = timestamp

	gps_dataset["x"] = new_x
	gps_dataset["y"] = new_y
	gps_dataset["z"] = new_z

	return gps_dataset


def _write_txyz_csv(gps_dataset: dict[str, list]):
	write_path = "data/intermediate/gps.csv"
	safe_makedirs(os.path.dirname(write_path))

	keys = ["timestamp", "x", "y", "z"]
	with open(write_path, "w", newline="") as f:
		writer = csv.writer(f)

		writer.writerow(keys)  # header

		for row in zip(*(gps_dataset[k] for k in keys)):  # rows from columns
			writer.writerow(row)


def _write_oxts_txt(gps_dataset: dict[str, any]):
	write_path = "data/intermediate/PDB/tracking/test/oxts/0000.txt"
	safe_makedirs(os.path.dirname(write_path))

	n = min(len(v) for v in gps_dataset.values() if v is not None)
	keys = list(OXTS_DEFAULT_VALUES.keys())

	if "z" in gps_dataset and "alt" not in gps_dataset:
		gps_dataset["alt"] = gps_dataset["z"]

	with open(write_path, "w") as f:
		for row_i in range(n):
			row = []

			for key in keys:
				gps_row = gps_dataset.get(key, None)

				value = OXTS_DEFAULT_VALUES.get(key, None)
				if gps_row is not None:
					value = gps_row[row_i]

				if value is None:
					raise ValueError(
						f"Missing required OXTS value '{key}' at row {row_i}. "
						f"Either provide it in gps_dataset or set a default."
					)

				row.append(value)

			row_str = " ".join(str(elem) for elem in row)
			f.write(row_str + "\n")


def main(data_dir_path: str, gps_file_path: str):
	# load & format data
	raw_gps_dataframe = _load_gps_dataframe(os.path.join(data_dir_path, gps_file_path))
	gps_dataset = _format_gpd_dataframe(raw_gps_dataframe)

	# apply kalman filter
	gps_dataset = _apply_kalman_filter(gps_dataset)

	_write_txyz_csv(gps_dataset)
	_write_oxts_txt(gps_dataset)


if __name__ == "__main__":
	import argparse

	# parse args
	parser = argparse.ArgumentParser(
		description="Smooth position using Kalman Filter. Reformat into tracker and oxt formats."
	)
	parser.add_argument(
		"data_dir_path",
		type=str,
		help="Path to the directory containing all data.",
	)
	parser.add_argument(
		"gps_file_path",
		type=str,
		help="Path to the csv file containing the gps data relative to DATA_DIR_PATH.",
	)
	args = parser.parse_args()

	# extract parameters
	DATA_DIR_PATH = (
		os.environ["DATA_DIR_PATH"]
		if "DATA_DIR_PATH" in os.environ
		else args.data_dir_path
	)
	GPS_FILE_PATH = (
		os.environ["GPS_FILE_PATH"]
		if "GPS_FILE_PATH" in os.environ
		else args.gps_file_path
	)

	main(DATA_DIR_PATH, GPS_FILE_PATH)
