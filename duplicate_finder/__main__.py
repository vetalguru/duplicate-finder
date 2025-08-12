# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from duplicate_finder.cli_args import ArgumentParserAdapter
from duplicate_finder.duplicate_finder import DuplicateFinder
from duplicate_finder.duplicate_finder_config import DuplicateFinderConfig


def main() -> None:
    # Parse command-line arguments (folder path, flags, etc.)
    args = ArgumentParserAdapter().parse()

    config = DuplicateFinderConfig(
        scan_folder_path=args.folder_path,
        exclude_patterns=args.exclude,
        include_patterns=args.include,
        max_file_size_str=args.max_size,
        min_file_size_str=args.min_size,
        output_file_path=args.output,
        sort_by_group_size=args.sort_by_group_size,
        sort_by_file_size=args.sort_by_file_size,
        threads_count=args.threads,
        verify_content=args.verify_content,
        delete_duplicates=args.delete,
        delete_report_file_path=args.delete_report,
        interactive_mode=args.interactive,
        dry_run=args.dry_run,
    )

    finder = DuplicateFinder()
    finder.run(config=config)


# Allow running the script directly
if __name__ == "__main__":
    main()
