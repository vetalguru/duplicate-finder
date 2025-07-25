# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

import argparse


class ArgumentParserAdapter:
    def __init__(self):
        # Initialize the argument parser with a description
        self.parser = argparse.ArgumentParser(
            prog="duplicate-finder",
            description="Script to find and delete duplicates of the files",
            formatter_class=argparse.RawTextHelpFormatter
        )
        self._add_arguments()

    def _add_arguments(self):
        self.parser.add_argument(
            "folder_path",
            type=str,
            help="Mandatory parameter: path to folder for search",
        )

        # Optional mutually exclusive flags for sorting strategy
        sort_group = self.parser.add_mutually_exclusive_group()
        sort_group.add_argument(
            "--sort-by-group-size",
            action="store_true",
            help="Optional: Sort duplicate groups by number"
            " of files in group (descending)",
        )
        sort_group.add_argument(
            "--sort-by-file-size",
            action="store_true",
            help="Optional: Sort duplicate groups by file size (descending)",
        )

        self.parser.add_argument(
            "--output",
            type=str,
            help="Optional: path to output file (e.g., duplicates.txt)",
        )
        self.parser.add_argument(
            "--exclude",
            type=str,
            nargs="*",
            default=[],
            help=(
                "Optional: list of exclude patterns (supports wildcards).\n"
                "Use Unix-style glob syntax:\n"
                "  *.log          - exclude all .log files\n"
                "  temp/*         - exclude files in any 'temp' subdirectory\n"
                "  **/.git/**     - exclude everything inside .git folders"
                " (recursive)\n"
                "Patterns are matched against full POSIX-style paths."
            ),
        )
        self.parser.add_argument(
            "--include",
            type=str,
            nargs="*",
            default=[],
            help=(
                "Optional: list of include patterns (supports wildcards).\n"
                "Use Unix-style glob syntax:\n"
                "  *.log          - include just .log files\n"
                "  temp/*         - include files in any 'temp' subdirectory\n"
                "  **/.git/**     - include everything inside .git"
                " folders (recursive)\n"
                "Patterns are matched against full POSIX-style paths."
            )
        )
        self.parser.add_argument(
            "--delete",
            action="store_true",
            help="Optional: delete duplicate files (keep first file in group)"
        )
        self.parser.add_argument(
            "--delete-report",
            type=str,
            help="Optional: path to report file where deleted"
            " file paths will be saved",
        )
        self.parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Optional: Show a list of files to be deleted"
            " without actually deleting them",
        )
        self.parser.add_argument(
            "--interactive",
            action="store_true",
            help="Optional: interactive mode, select files"
                 " to delete group by group",
        )

        self.parser.add_argument(
            "--threads",
            type=int,
            default=None,
            help="Optional: Number of threads."
                 " Dynamically adjusted by default",
        )

        self.parser.add_argument(
            "--min-size",
            type=str,
            default=None,
            help="Optional: Minimum file size to consider for"
                 " duplicate detection (e.g. 100K, 5M, 1G)"
        )

        self.parser.add_argument(
            "--max-size",
            type=str,
            default=None,
            help="Optional: Maximum file size to consider for"
                 " duplicate detection (e.g. 100K, 5M, 1G)"
        )

        self.parser.add_argument(
            "--verify-content",
            action="store_true",
            help="Optional: Compare files byte by byte to verify"
                 " they are identical (default is to compare file sizes only)"
        )

    def parse(self) -> argparse.Namespace:
        # Parse and return the command-line arguments
        return self.parser.parse_args()
