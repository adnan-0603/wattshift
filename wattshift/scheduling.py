"""Pure deterministic scheduling primitives shared by replay and live controller.

All slots must have the same duration, no missing price, and no assumed
instantaneous/preemptive GPU migration.  Indices use [release, deadline).
"""
import math


def best_start(signal, release: int, deadline: int, length: int):
    """Earliest minimum-sum contiguous window; None when no complete window.

    Linear time, unlike repeatedly building O(length) slices for each candidate.
    A missing/non-finite observation invalidates only windows containing it.
    Costs differing by less than 1e-9 EUR/MWh are treated as ties so floating
    sliding-sum drift cannot change an otherwise identical scheduling decision.
    """
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in (release, deadline, length)):
        raise ValueError('Slot indices and duration must be integers')
    if release < 0 or deadline > len(signal) or deadline < release or length < 1:
        raise ValueError('Invalid scheduling slot bounds')
    best, best_value, running, valid = None, float('inf'), 0.0, 0
    for i in range(release, deadline):
        value = signal[i]
        if value is None or not math.isfinite(float(value)):
            running, valid = 0.0, 0
            continue
        running += float(value)
        valid += 1
        if valid > length:
            running -= float(signal[i-length])
            valid -= 1
        if valid == length and math.isfinite(running) and (best is None or running < best_value - 1e-9):
            best_value, best = running, i-length+1
    return best
