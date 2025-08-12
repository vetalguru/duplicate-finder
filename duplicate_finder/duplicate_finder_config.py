# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from duplicate_finder.utils import str_file_size_to_int


@dataclass
class DuplicateFinderConfig:
    """
    Configuration class for the Duplicate Finder module.
    """

    # The folder path to search for duplicate files.
    # This should be a valid path to a directory.
    scan_folder_path: str

    # Patterns to exclude from the search.
    # This can be a list of strings or None to include all files.
    # If None, no files will be excluded.
    # If exclude_patterns is specified, files matching these
    # patterns will be ignored.
    exclude_patterns: Optional[List[str]] = None

    # Patterns to include in the search.
    # This can be a list of strings or None to include all files.
    # If None, ALL files will be included.
    # If include_patterns is specified, only files matching these
    # patterns will be considered.
    # If both exclude_patterns and include_patterns are specified,
    # include_patterns will take precedence.
    include_patterns: Optional[List[str]] = None

    # The maximum file size to consider for duplicates.
    # This can be a string representing a human-readable
    # size (e.g., '10MB', '2.5 GiB').
    # If None, no size limit will be applied.
    max_file_size_str: Optional[str] = None

    # The maximum file size in bytes.
    # Calculates from max_file_size_str
    max_file_size: Optional[int] = None

    # The minimum file size to consider for duplicates.
    # This can be a string representing a human-readable
    # size (e.g., '10MB', '2.5 GiB').
    # If None, no size limit will be applied.
    min_file_size_str: Optional[str] = None

    # The minimum file size in bytes.
    # Calculates from min_file_size_str
    min_file_size: Optional[int] = None

    # The output file path where the results will be saved.
    # If None, results will not be saved to a file.
    output_file_path: Optional[str] = None

    # Flag to sort duplicate groups by the number of files in each group.
    # If True, groups will be sorted by size (descending).
    # If False, groups will not be sorted by size.
    # This is mutually exclusive with sort_by_file_size.
    sort_by_group_size: bool = False

    # Flag to sort duplicate groups by file size.
    # If True, groups will be sorted by file size (descending).
    # If False, groups will not be sorted by file size.
    sort_by_file_size: bool = False

    # The number of threads to use for parallel processing.
    # If None, the default number of threads will be used.
    threads_count: int = 0

    # Flag to byte-by-byte verify the content of files.
    # If True, files will be verified by comparing their content.
    verify_content: bool = False

    # Delete duplicate files (keep first file in group)
    # If True, duplicate files will be deleted, keeping only
    # the first file in each group.
    # If False, duplicate files will not be deleted.
    # Note: This is a potentially destructive operation,
    # so use with caution.
    delete_duplicates: bool = False

    # Path to a report file where deleted file paths will be saved.
    # If None, no report will be generated.
    delete_report_file_path: Optional[str] = None

    # Flag to enable interactive mode.
    # If True, the user will be prompted for confirmation before deleting files.
    # If False, files will be deleted without confirmation.
    # This is useful for manual review of duplicates before deletion.
    # Note: This is only applicable if delete_duplicates is True.
    interactive_mode: bool = False

    # Flag to enable dry run mode.
    # If True, the program will show a list of files to be deleted
    # without actually deleting them. This is useful for reviewing
    # which files would be deleted. If False, files will be deleted
    # as per the delete_duplicates setting.
    # Note: This is only applicable if delete_duplicates is True.
    dry_run: bool = False

    def __post_init__(self) -> None:
        """
        Post-initialization method to normalize and validate
        the configuration parameters.
        """
        self.scan_folder_path = self.normalize_dir_path(self.scan_folder_path)
        self.exclude_patterns = self.normalize_pattern(self.exclude_patterns)
        self.include_patterns = self.normalize_pattern(self.include_patterns)
        self.max_file_size = (
            self.normalize_str_file_size(self.max_file_size_str))
        self.min_file_size = (
            self.normalize_str_file_size(self.min_file_size_str))
        self.output_file_path = self.normalize_file_path(self.output_file_path)
        self.threads_count = self.normalize_threads_counter(self.threads_count)
        self.delete_report_file_path = self.normalize_file_path(
            self.delete_report_file_path
        )

    # Utility functions for normalization
    @staticmethod
    def normalize_dir_path(folder_path: str) -> str:
        """
        Normalize the provided folder path to ensure it is a valid Path object
        """
        path = Path(folder_path).resolve()
        if not path.is_dir():
            raise ValueError(f"Provided path '{folder_path}'"
                             f" is not a directory.")
        return str(path)

    @staticmethod
    def normalize_file_path(file_path: str | None) -> str | None:
        """
        Normalize the output report path to ensure it is a valid Path object.
        """
        if file_path is None:
            return None
        return str(Path(file_path).resolve())

    @staticmethod
    def normalize_pattern(patterns: list[str] | None) -> list[str] | None:
        """
        Normalize a list of patterns by stripping
        whitespace and removing empty strings.
        """
        if patterns is None:
            return None
        return [pattern.strip() for pattern in patterns if pattern.strip()]

    @staticmethod
    def normalize_str_file_size(size: str | None) -> int | None:
        """
        Normalize a size string to an integer in bytes.
        """
        if size is None:
            return None

        # Check if the size string has a valid number format
        match = re.match(
            r"^\s*(\d*\.?\d*)\s*([KMGT]?I?B)?\s*$",
            size,
            re.IGNORECASE)
        if not match:
            raise ValueError(
                f"Invalid size format '{size}': must contain a valid number"
            )

        number, unit = match.groups()
        if not number or number == ".":
            raise ValueError(f"Invalid number format in size '{size}'")

        try:
            return str_file_size_to_int(size)
        except ValueError as e:
            raise ValueError(f"Invalid size format '{size}': {e}") from e

    @staticmethod
    def normalize_threads_counter(threads: int) -> int:
        """
        Normalize the number of threads to a reasonable value.
        """
        # Normalize threads count to a reasonable value
        if threads is None or threads <= 0:
            return min(32, os.cpu_count() or 8)
        if threads > 32:
            print(
                f"WARNING: Using {threads} threads, "
                "which is more than the recommended maximum of 32."
            )
        return threads
