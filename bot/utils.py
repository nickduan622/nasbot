"""Shared utilities."""


def fmt_bytes(b: int | float) -> str:
    if b >= 1024 ** 4:
        return f"{b / 1024 ** 4:.2f} TB"
    if b >= 1024 ** 3:
        return f"{b / 1024 ** 3:.1f} GB"
    if b >= 1024 ** 2:
        return f"{b / 1024 ** 2:.1f} MB"
    return f"{b / 1024:.0f} KB"
