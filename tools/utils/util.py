def whole_number_to_label(n: int) -> str:
    if n < 1e3:
        return f"{n}"
    elif n < 1e6:
        return f"{int(round(n / 1e3, 2))}K"
    elif n < 1e9:
        return f"{int(round(n / 1e6, 2))}M"
    elif n < 1e12:
        return f"{int(round(n / 1e9, 2))}G"
    else:
        return f"{int(round(n / 1e12, 2))}T"


def order_mag_to_multiplier(mag: int) -> tuple[int, str]:
    if mag < 3:
        return 1, ""
    elif mag < 6:
        return 3, "K"
    elif mag < 9:
        return 6, "M"
    elif mag < 12:
        return 9, "G"
    return 12, "T"


def number_to_multiplier(n: float) -> tuple[int, str]:
    order_mag = -1
    while round(n / 10, 1) != 0:
        n /= 10
        order_mag += 1

    multiplier, suffix = order_mag_to_multiplier(order_mag)
    return multiplier, suffix


# Returns (avg, err, multiplier suffix)
def avg_err_precision_to_label(avg: float, err: float) -> tuple[str, str, str]:
    if err == 0:
        multiplier, suffix = number_to_multiplier(avg)
        return str(avg // 10**multiplier), "0", suffix

    order_mag = -1
    while round(err / 10, 1) != 0:
        avg /= 10
        err /= 10
        order_mag += 1

    avg = round(avg, 1)
    err = round(err, 1)

    avg = int(avg * 10)
    err = int(err * 10)

    multiplier, suffix = order_mag_to_multiplier(order_mag)
    order_mag -= multiplier

    avg = int(avg * 10**order_mag)
    err = int(err * 10**order_mag)

    return str(avg), str(err), suffix
