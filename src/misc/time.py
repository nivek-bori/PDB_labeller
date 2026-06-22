def get_ns_timestamp(timestamp) -> int:
    import datetime
    import re

    if isinstance(timestamp, int):
        if timestamp > 1e14:  # >3,000 years in ns
            return timestamp
        return int(timestamp * 1e9)
    elif isinstance(timestamp, float):
        return int(timestamp * 1e9)
    elif not isinstance(timestamp, str):
        raise TypeError("timestamp must be str, int, or float")

    ts = timestamp.strip()
    # 1. Try pure integer string (filename with epoch maybe)
    if re.fullmatch(r"\d{10,20}", ts):
        value = int(ts)
        if value > 1e14:  # likely ns
            return value
        return int(value * 1e9)
    # 2. Try ISO or similar
    try:
        # Try with nanosecond-level
        if "." in ts:
            # ISO with micro-/nano-, e.g., 2024-06-11T17:22:17.123456789
            match = re.match(r"(\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d)(\.\d+)?(Z)?", ts)
            if match:
                base = match.group(1)
                frac = match.group(2)[1:] if match.group(2) else "0"
                # Fill to 9 digits for ns
                frac = (frac + "000000000")[:9]
                dt = datetime.datetime.fromisoformat(base)
                epoch = datetime.datetime(1970, 1, 1, tzinfo=dt.tzinfo)
                ns = int((dt - epoch).total_seconds()) * 1_000_000_000
                ns += int(frac)
                return ns
        # Try normal fromisoformat (no ns)
        dt = datetime.datetime.fromisoformat(ts)
        epoch = datetime.datetime(1970, 1, 1, tzinfo=dt.tzinfo)
        return int((dt - epoch).total_seconds() * 1e9)
    except Exception:
        pass

    # 3. Try parsing file names of the form .../1707888323146814000.jpg
    stem = ts
    if "." in ts:
        stem = ts.split(".")[0]
    if re.fullmatch(r"\d{10,20}", stem):
        value = int(stem)
        if value > 1e14:
            return value
        return int(value * 1e9)

    raise ValueError(f"Could not parse timestamp: {timestamp}")
