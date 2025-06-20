from cli_args import ArgumentParserAdapter
from finder import DuplicateFinder

def main() -> None:
    args = ArgumentParserAdapter().parse()

    finder = DuplicateFinder(args.folder_path, exclude_patterns=args.exclude)
    finder.run(
        sort_by_group=args.sort_by_group_size,
        sort_by_size=args.sort_by_file_size,
        output_path=args.output,
        delete=args.delete,
        interactive=args.interactive,
        dry_run=args.dry_run,
        delete_report=args.delete_report,
        threads=args.threads
)

if __name__ == "__main__":
    main()
