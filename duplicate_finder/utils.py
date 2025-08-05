# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

import hashlib
import re
from pathlib import Path


def calc_file_sha256(file_path: Path, block_size: int = 65536) -> str:
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


def int_file_size_to_str(size_bytes: int) -> str:
    """
    Convert a file size in bytes to a human-readable string (e.g., '1.2 MB').

    Args:
        size_bytes (int): The size in bytes.

    Returns:
        str: Human-readable file size, or 'Invalid size' for invalid input.
    """
    if (size_bytes is None or
            not isinstance(size_bytes, (int, float)) or size_bytes < 0):
        return "Invalid size"

    tmp_size_bytes = float(size_bytes)

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if tmp_size_bytes < 1024:
            return (
                f"{int(tmp_size_bytes)} {unit}"
                if unit == "B"
                else f"{tmp_size_bytes:.1f} {unit}"
            )
        tmp_size_bytes /= 1024
    return f"{tmp_size_bytes:.1f} PB"


def files_are_identical(
        file1: Path,
        file2: Path,
        chunk_size: int = 65536) -> bool:
    """
    Check if two files are identical by comparing their SHA256 hashes.

    Args:
        file1 (Path): First file path.
        file2 (Path): Second file path.
        chunk_size (int): Size of chunks to read from files for comparison.

    Returns:
        bool: True if files are identical, False otherwise.
    """
    if file1.stat().st_size != file2.stat().st_size:
        return False

    with open(file1, "rb") as f1, open(file2, "rb") as f2:
        while True:
            b1 = f1.read(chunk_size)
            b2 = f2.read(chunk_size)
            if b1 != b2:
                return False
            if not b1:  # EOF
                return True
