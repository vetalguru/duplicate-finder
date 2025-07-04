# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

import hashlib
import re


def calc_file_sha256(file_path: str, block_size: int = 65536) -> str:
    """Compute SHA256 hash for a given file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(block_size), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def str_file_size_to_int(size_str: str) -> int:
    """
    Convert a human-readable file size string (e.g., '10MB', '2.5 GiB',
    '100K') to an integer number of bytes.

    Supports both decimal (KB, MB, GB, TB) and binary (KiB, MiB, GiB,
    TiB) units.
    Raises ValueError for invalid or unknown units.
    """
    match = re.fullmatch(
        r"\s*([\d.]+)\s*([KMGT]?I?B?)?\s*", size_str.strip(), re.IGNORECASE
    )
    if not match:
        raise ValueError(f"Invalid size string: {size_str}")

    number, unit = match.groups()
    unit = (unit or "").upper()
    units = {
        "B": 1,
        "K": 10**3,
        "KB": 10**3,
        "M": 10**6,
        "MB": 10**6,
        "G": 10**9,
        "GB": 10**9,
        "T": 10**12,
        "TB": 10**12,
        "KI": 2**10,
        "KIB": 2**10,
        "MI": 2**20,
        "MIB": 2**20,
        "GI": 2**30,
        "GIB": 2**30,
        "TI": 2**40,
        "TIB": 2**40,
        "": 1,
        None: 1,
    }
    if unit not in units:
        raise ValueError(f"Unknown size unit: {unit}")
    return int(float(number) * units[unit])
