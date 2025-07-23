import os
import argparse
import json


def aggregate_files_to_json(config):
    """
    Recursively finds files based on the provided configuration and writes
    their path and content to a JSON output file.

    Args:
        config (dict): A dictionary containing all configuration parameters,
                       including directory, inclusions, and exclusions.
    """
    aggregated_data = []

    # Use os.walk to traverse the directory tree.
    # We will modify dirnames in-place to prune the search, which is efficient.
    for dirpath, dirnames, filenames in os.walk(config['dir'], topdown=True):

        # --- Directory Exclusion ---
        # Remove excluded directories from the list of directories to visit.
        # This is the efficient way to prevent os.walk from descending into them.
        dirnames[:] = [d for d in dirnames if d not in config['exclude_dirs']]

        for filename in filenames:
            # --- File Exclusion ---
            # Check if the file should be excluded by its name or extension.
            is_excluded_file = filename in config['exclude_files']
            is_excluded_ext = any(filename.endswith(ext)
                                  for ext in config['exclude_exts'])

            if is_excluded_file or is_excluded_ext:
                continue

            # --- File Inclusion ---
            # Check if the file should be included by its name or extension.
            should_include_by_name = filename in config['file']
            should_include_by_ext = any(filename.endswith(ext)
                                        for ext in config['ext'])

            if should_include_by_name or should_include_by_ext:
                full_path = os.path.join(dirpath, filename)
                try:
                    # Get the path relative to the starting search directory.
                    relative_path = os.path.relpath(full_path, config['dir'])

                    # Get the base name of the input directory to prepend to the path.
                    # os.path.abspath handles cases like '.' or '..'
                    base_dir_name = os.path.basename(
                        os.path.abspath(config['dir']))

                    # Construct the final display path.
                    display_path = os.path.join(base_dir_name, relative_path)

                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as infile:
                        content = infile.read()
                        aggregated_data.append({
                            "filePath": display_path,
                            "content": content
                        })
                except Exception as e:
                    print(f"Error reading file {full_path}: {e}")

    # Write the aggregated data to the output file.
    try:
        with open(config['output'], 'w', encoding='utf-8') as outfile:
            json.dump(aggregated_data, outfile, indent=2)
        print(
            f"Successfully aggregated {len(aggregated_data)} files into {config['output']}")
    except IOError as e:
        print(f"Error writing to output file {config['output']}: {e}")


def load_config(config_path):
    """Loads configuration from a JSON file if it exists."""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def main():
    """
    Parses command-line arguments, loads config file, merges settings,
    and initiates the file aggregation.
    """
    parser = argparse.ArgumentParser(
        description="Aggregates the content of specified files from a directory "
                    "into a single JSON file, with support for a config file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # --- Arguments Definition ---
    parser.add_argument('-c', '--config', type=str,
                        default='.aicodec-config.json', help="Path to the configuration file.")
    parser.add_argument('-d', '--dir', type=str,
                        help="The directory to search.")
    parser.add_argument('-o', '--output', type=str,
                        help="The name of the output JSON file.")

    # Inclusion arguments
    parser.add_argument('-e', '--ext', action='append',
                        help="File extension to include. Can be used multiple times.")
    parser.add_argument('-f', '--file', action='append',
                        help="Specific filename to include. Can be used multiple times.")

    # Exclusion arguments
    parser.add_argument('--exclude-dir', action='append',
                        help="Directory to exclude. Can be used multiple times.")
    parser.add_argument('--exclude-ext', action='append',
                        help="File extension to exclude. Can be used multiple times.")
    parser.add_argument('--exclude-file', action='append',
                        help="Specific filename to exclude. Can be used multiple times.")

    args = parser.parse_args()

    # --- Configuration Merging Logic ---
    # 1. Start with hardcoded defaults.
    config = {
        'dir': '.',
        'output': 'aggregated_content.json',
        'ext': [],
        'file': [],
        'exclude_dirs': ['.git', 'node_modules', '__pycache__', '.venv', 'dist', 'build'],
        'exclude_exts': ['.log', '.tmp', '.bak', '.swo', '.swp'],
        'exclude_files': ['.DS_Store']
    }

    # 2. Load settings from the config file and update the defaults.
    file_config = load_config(args.config)
    config.update(file_config)

    # 3. Override with any command-line arguments provided by the user.
    if args.dir is not None:
        config['dir'] = args.dir
    if args.output is not None:
        config['output'] = args.output
    if args.ext is not None:
        config['ext'] = list(set(config['ext'] + args.ext)
                             )  # Merge and deduplicate
    if args.file is not None:
        config['file'] = list(set(config['file'] + args.file))
    if args.exclude_dir is not None:
        config['exclude_dirs'] = list(
            set(config['exclude_dirs'] + args.exclude_dir))
    if args.exclude_ext is not None:
        config['exclude_exts'] = list(
            set(config['exclude_exts'] + args.exclude_ext))
    if args.exclude_file is not None:
        config['exclude_files'] = list(
            set(config['exclude_files'] + args.exclude_file))

    # Ensure all extensions start with a dot for consistency.
    config['ext'] = [e if e.startswith(
        '.') else '.' + e for e in config['ext']]
    config['exclude_exts'] = [e if e.startswith(
        '.') else '.' + e for e in config['exclude_exts']]

    if not config['ext'] and not config['file']:
        parser.error(
            "No files to aggregate. Please provide inclusions in your config file or via command-line arguments.")

    aggregate_files_to_json(config)


if __name__ == "__main__":
    main()
