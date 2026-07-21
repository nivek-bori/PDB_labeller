from collections.abc import Iterable


def calculate_interpolate(a_t, b1_t, b2_t, b1_val, b2_val):
	if b2_t == b1_t:
		return b1_val

	ratio = (a_t - b1_t) / (b2_t - b1_t)
	return (b2_val - b1_val) * ratio + b1_val


def interpolate(a: list[any], b: list[any], get_a_time, get_b_time, get_b_value) -> list[tuple[int, any]]:
    a.sort(key=get_a_time)
    b.sort(key=get_b_time)

    n_a, n_b = len(a), len(b)
    a = [{"idx": i, "type": "a"} for i in range(n_a)]

    # keep b items that can be interpoalted (are between a items)
    min_a_time, max_a_time = get_a_time(a[0]), get_a_time(a[-1])
    b = [
        {"idx": i, "type": "b"}
        for i in range(n_b)
        if (min_a_time <= get_b_time(b[i]) and get_b_time(b[i]) <= max_a_time)
    ]

    ab = sorted(
        a + b,
        key=lambda item: (
            get_a_time(a[item["idx"]]) if item["type"] == "a" else get_b_time(b[item["idx"]]),
            0 if item["type"] == "b" else 1,
        ),
    )

    interpolated_b = []

    prev_b_idx = None
    for item in ab:
        if item["type"] == "b":
            prev_b_idx = item["idx"]
            continue

        # type == a
        curr_a = a[item["idx"]]
        prev_b = b[prev_b_idx]

        # direct match
        if get_b_time(prev_b) == get_a_time(curr_a):
            interpolated_b.append((get_a_time(curr_a), get_b_value(prev_b)))
            continue

        # interpolate
        next_b = b[prev_b_idx + 1]
        prev_b_val = get_b_value(prev_b)

        # b values is iterable
        if isinstance(prev_b_val, Iterable) and not isinstance(prev_b_val, (str, bytes)):
            n = range(prev_b_val)
            interpolated_b_vals = [
                calculate_interpolate(
                    a_t=get_a_time(curr_a),
                    b1_t=get_b_time(prev_b),
                    b2_t=get_b_time(next_b),
                    b1_val=prev_b_val[i],
                    b2_val=get_b_value(next_b)[i],
                )
                for i in n
            ]
            interpolated_b.append((get_a_time(curr_a), interpolated_b_vals))
        else:
            # b value is non-iterable
            interpolated_b_val = calculate_interpolate(
                a_t=get_a_time(curr_a),
                b1_t=get_b_time(prev_b),
                b2_t=get_b_time(next_b),
                b1_val=prev_b_val,
                b2_val=get_b_value(next_b),
            )
            interpolated_b.append((get_a_time(curr_a), interpolated_b_val))

    return interpolated_b
