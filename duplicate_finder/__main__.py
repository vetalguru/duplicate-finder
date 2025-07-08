# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from pathlib import Path
from .cli_args import ArgumentParserAdapter
from .duplicate_finder import DuplicateFinder


def main() -> None:
    # Parse command-line arguments (folder path, flags, etc.)
    args = ArgumentParserAdapter().parse()

    finder = DuplicateFinder()
    finder.run(
        folder_path=Path(args.folder_path),
        exclude_patterns=args.exclude,
        include_patterns=args.include,
        min_size=args.min_size,
        max_size=args.max_size,
        sort_by_group=args.sort_by_group_size,
        sort_by_size=args.sort_by_file_size,
        output_report_path=args.output,
        delete=args.delete,
        interactive=args.interactive,
        dry_run=args.dry_run,
        delete_report_path=args.delete_report,
        threads=args.threads,
    )


# Allow running the script directly
if __name__ == "__main__":
    main()
