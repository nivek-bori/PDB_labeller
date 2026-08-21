import math
import numpy as np


def _best_grid_phase(timestamps, weights, period):
    """
    Find the phase in [0, period) that minimizes weighted squared
    distance from each timestamp to the nearest point on the grid.
    """
    residuals = np.mod(timestamps, period)

    order = np.argsort(residuals)
    residuals = residuals[order]
    weights = weights[order]

    n = len(residuals)
    total_weight = np.sum(weights)

    # Prefix sums let us test every possible circular "cut"
    # efficiently.
    prefix_w = np.concatenate(([0.0], np.cumsum(weights)))
    prefix_wr = np.concatenate(([0.0], np.cumsum(weights * residuals)))
    prefix_wr2 = np.concatenate(([0.0], np.cumsum(weights * residuals**2)))

    sum_wr = prefix_wr[-1]
    sum_wr2 = prefix_wr2[-1]

    best_error = float("inf")
    best_phase = None

    for cut_i in range(n):
        # Residuals before the cut are shifted up by one period,
        # converting the circular problem into an ordinary mean.
        shifted_weight = prefix_w[cut_i]
        shifted_wr = prefix_wr[cut_i]

        sum_x = sum_wr + period * shifted_weight
        sum_x2 = sum_wr2 + 2 * period * shifted_wr + period**2 * shifted_weight

        mean = sum_x / total_weight

        # Check that this circular unwrapping is valid:
        # all timestamps must be within half a period of the mean.
        min_x = residuals[cut_i]
        max_x = residuals[cut_i - 1] + period if cut_i > 0 else residuals[-1]

        if min_x < mean - period / 2 or max_x > mean + period / 2:
            continue

        error = sum_x2 - sum_x**2 / total_weight

        if error < best_error:
            best_error = error
            best_phase = mean % period

    return best_phase


def unify_timestamps(timestamp_lists, hz):
    """
    Create a fixed-frequency timestamp grid that best aligns with
    multiple timestamp sequences.

    Each input sequence receives equal weight, regardless of how many
    timestamps it contains.

    Parameters
    ----------
    timestamp_lists : list[list[float]]
        Timestamp sequences from multiple data sources.
    hz : float
        Desired output frequency.

    Returns
    -------
    list[float]
        Uniform timestamps spanning the common time range of all sources.
    """
    if hz <= 0:
        raise ValueError("hz must be greater than 0")

    if not timestamp_lists:
        return []

    timestamp_lists = [np.asarray(times, dtype=float) for times in timestamp_lists]

    if any(len(times) == 0 for times in timestamp_lists):
        raise ValueError("timestamp lists cannot be empty")

    # Sort each source.
    timestamp_lists = [np.sort(times) for times in timestamp_lists]

    period = 1.0 / hz

    # Give every source the same total weight.
    timestamps = []
    weights = []

    for times in timestamp_lists:
        timestamps.extend(times)

        source_weight = 1.0 / len(times)
        weights.extend([source_weight] * len(times))

    timestamps = np.asarray(timestamps)
    weights = np.asarray(weights)

    # Find the optimal placement of the fixed-frequency grid.
    phase = _best_grid_phase(
        timestamps,
        weights,
        period,
    )

    # Only return timestamps where every source has data available.
    start_time = max(times[0] for times in timestamp_lists)
    end_time = min(times[-1] for times in timestamp_lists)

    if start_time > end_time:
        return []

    # Find integer grid indices inside the overlap.
    first_i = math.ceil((start_time - phase) / period)
    last_i = math.floor((end_time - phase) / period)

    if first_i > last_i:
        return []

    return [phase + i * period for i in range(first_i, last_i + 1)]
