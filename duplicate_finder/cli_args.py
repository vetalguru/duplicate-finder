import argparse


class ArgumentParserAdapter:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="Script to find and delete duplicates of the files")
        self._add_arguments()

    def _add_arguments(self):
        self.parser.add_argument(
            'folder_path',
            type=str,
            help="Mandatory parameter: path to folder for search")
        sort_group = self.parser.add_mutually_exclusive_group()
        sort_group.add_argument(
            '--sort-by-group-size',
            action='store_true',
            help="Optional: Sort duplicate groups by number of files in group (descending)")
        sort_group.add_argument(
            '--sort-by-file-size',
            action='store_true',
            help="Optional: Sort duplicate groups by file size (descending)")
        self.parser.add_argument(
            '--output', '-o',
            type=str,
            help="Optional: path to output file (e.g., duplicates.txt)")
        self.parser.add_argument(
            '--exclude', '-e',
            type=str,
            nargs='*',
            default=[],
            help=(
                "Optional: list of exclude patterns (supports wildcards).\n"
                "Use Unix-style glob syntax:\n"
                "  *.log          — exclude all .log files\n"
                "  temp/*         — exclude files in any 'temp' subdirectory\n"
                "  **/.git/**     — exclude everything inside .git folders (recursive)\n"
                "Patterns are matched against full POSIX-style paths."
            ))
        self.parser.add_argument(
            '--delete',
            action='store_true',
            help="Optional: delete duplicate files (keep first file in group)")
        self.parser.add_argument(
            '--delete-report',
            type=str,
            help="Optional: path to report file where deleted file paths will be saved")
        self.parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Optional: Show a list of files to be deleted without actually deleting them")
        self.parser.add_argument(
            '--threads',
            type=int,
            default=8,
            help="Optional: Number of threads (Default value: 8)")

    def parse(self) -> argparse.Namespace:
        return self.parser.parse_args()
