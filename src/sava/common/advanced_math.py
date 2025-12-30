
# round to the nearest int number n in [min_value, max_value] range, which is n % div == mod % div
def advanced_round(x: float, div: int, mod: int = 0, min_value: int = None, max_value: int = None) -> int:
    mod = mod % div

    base_value = round(x)
    remainder = base_value % div

    if remainder == mod and (min_value is None or base_value >= min_value) and (max_value is None or base_value <= max_value):
        return base_value

    # Calculate distances to the nearest values that satisfy n % div == mod
    lower_candidate = base_value - remainder + mod
    upper_candidate = lower_candidate + div

    # If mod > remainder, we need to check the previous cycle
    if mod > remainder:
        lower_candidate -= div
        upper_candidate -= div
    
    # Apply range constraints
    candidates = []
    
    # Check lower candidate
    if (min_value is None or lower_candidate >= min_value) and (max_value is None or lower_candidate <= max_value):
        candidates.append(lower_candidate)

    # Check upper candidate
    if (min_value is None or upper_candidate >= min_value) and (max_value is None or upper_candidate <= max_value):
        candidates.append(upper_candidate)
    
    # If no candidates within range, find the closest valid value
    if not candidates:
        # Find all valid values in the range
        if min_value is not None and max_value is not None:
            for n in range(min_value, max_value + 1):
                if n % div == mod:
                    candidates.append(n)
        else:
            # Expand search outward from the original candidates
            search_range = max(div, 10)  # reasonable search limit
            for offset in range(1, search_range):
                for candidate in [lower_candidate - div * offset, upper_candidate + div * offset]:
                    if (min_value is None or candidate >= min_value) and (max_value is None or candidate <= max_value):
                        candidates.append(candidate)
                        break
                if candidates:
                    break
    
    # Return the candidate closest to x
    if candidates:
        return min(candidates, key = lambda n: abs(x - n))
    else:
        # No valid candidates found - condition is impossible
        range_str = ""
        if min_value is not None and max_value is not None:
            range_str = f" in range [{min_value}, {max_value}]"
        elif min_value is not None:
            range_str = f" >= {min_value}"
        elif max_value is not None:
            range_str = f" <= {max_value}"

        raise ValueError(f"No integer{range_str} satisfies n % {div} == {mod}")


# return a number y that: min_value <= y < max_value (if one of the values is missing then the closest to the other), and y % div == x % div
def advanced_mod(x: float, div: int, min_value: float = None, max_value: float = None) -> float:
    # If no constraints, return x as-is
    if min_value is None and max_value is None:
        return x

    # Set default values if one is missing
    min_value = max_value - div if min_value is None else min_value
    max_value = min_value + div if max_value is None else max_value

    # Now both min_value and max_value are defined
    mod = x % div

    # If x is already in range, return it
    if min_value <= x < max_value:
        return x

    # Find the first value in [min_value, max_value) with the correct modulo
    # Calculate offset from min_value to first valid candidate
    offset = (mod - min_value % div) % div
    first_candidate = min_value + offset

    # Check if any candidates exist in range
    if first_candidate >= max_value:
        raise ValueError(f"No value in range [{min_value}, {max_value}) satisfies y % {div} == {x} % {div} (mod = {mod})")

    # Find the candidate closest to x
    if x < min_value:
        # x is below range, return the smallest candidate (closest to x)
        return first_candidate
    else:  # x >= max_value
        # x is above range, return the largest candidate (closest to x)
        # Find largest candidate < max_value
        num_steps = int((max_value - first_candidate - 1) / div)
        return first_candidate + num_steps * div
