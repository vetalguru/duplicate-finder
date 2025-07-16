<p align="center">
  <img src="assets/duplicate-finder_t.png" alt="Duplicate Finder Logo" width="200">
</p>

# Duplicate Finder

A **command-line tool** to efficiently find and delete duplicate files in a given folder.
Supports **interactive deletion**, exclusion patterns, and multi-threaded hashing for fast processing.

## 🚀 Features

- **Fast duplicate detection** using file size and SHA256 hashing
- **Interactive mode** for manual file selection
- **Dry-run mode** to preview deletions without modifying files
- **Exclusion patterns** to ignore specific files or folders
- **Multi-threaded hashing** for improved performance

## 🔧 Installation

Clone the repository:

```bash
git clone https://github.com/vetalguru/duplicate-finder.git
cd duplicate-finder
```

Run without installation:

```bash
python -m duplicate_finder --help
```

Or install as a package:

```bash
pip install .
```

## 📌 Usage

### Basic duplicate search:

```bash
python -m duplicate_finder "C:/Users/John/Documents"
```

### Interactive deletion:

```bash
python -m duplicate_finder "C:/Users/John/Documents" --interactive
```

### Automatic deletion (with confirmation):

```bash
python -m duplicate_finder "C:/Users/John/Documents" --delete
```

### Save deleted file paths to a report:

```bash
python -m duplicate_finder "C:/Users/John/Documents" --delete --delete-report deleted.txt
```

### Dry-run mode (preview deletions):

```bash
python -m duplicate_finder "C:/Users/John/Documents" --delete --dry-run
```

### Save results to a file:

```bash
python -m duplicate_finder "C:/Users/John/Documents" --output duplicates.txt
```

### Include only specific file types:

```bash
python -m duplicate_finder "C:/Users/John/Documents" --include "*.txt" "*.md"
```
### Exclude specific files or folders:

```bash
python -m duplicate_finder "C:/Users/John/Documents" --exclude "*.log" "temp/*"
```

### Skip small files (e.g., less than 100KB) and large ones (e.g., more than 100MB):

```bash
python -m duplicate_finder "C:/Users/John/Documents" --min-size 100K --max-size 100M
```


## ⚙️ CLI Options

| Option                 | Description                                             |
|------------------------|---------------------------------------------------------|
| `folder_path`          | **(Required)** Path to the folder to scan               |
| `--sort-by-group-size` | Sort duplicate groups by number of files                |
| `--sort-by-file-size`  | Sort duplicate groups by file size                      |
| `--output`             | Save duplicate list to a file                           |
| `--include`            | Include files/folders using glob patterns               |
| `--exclude`            | Exclude files/folders using glob patterns               |
| `--delete`             | Delete duplicate files (keeps first file in each group) |
| `--delete-report`      | Save deleted file paths to a report                     |
| `--dry-run`            | Show files that would be deleted without deleting them  |
| `--interactive`        | Interactive mode: manually select files to delete       |
| `--threads`            | Number of threads for hashing (calculated by default)   |
| `--max_size`           | Maximum file size to analyze                            |
| `--min_size`           | Minimal file size to analyze                            |

## 🛠 Development

To run tests:

```bash
pytest
```

To format code:

```bash
black .
```

## 📜 License

Licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
