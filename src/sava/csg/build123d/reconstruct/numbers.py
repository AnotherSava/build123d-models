def fmt(x: float, max_decimals: int = 3) -> str:
    if abs(x) < 0.5 * 10 ** (-max_decimals):
        return '0'
    rounded = round(x, max_decimals)
    if rounded == int(rounded):
        return f'{int(rounded)}'
    s = f'{rounded:.{max_decimals}f}'
    return s.rstrip('0').rstrip('.')
