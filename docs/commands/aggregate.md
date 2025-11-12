# `aicodec aggregate`

Scans your project based on your configuration, finds all relevant files, and aggregates their content into a single `.aicodec/context.json` file. This file is then used by `aicodec prompt` to build the context for the LLM.

By default, this command runs in an **incremental mode**. It caches file hashes and only includes content from files that have changed since the last run. This saves time and helps manage the size of the context sent to the LLM.

## Usage

```bash
# Run an incremental aggregation
aicodec aggregate

# Exclude all markdown files and include only the src/api directory
aicodec aggregate -e "*.md" -i "src/api/**"

# Run a full aggregation, ignoring the cache
aicodec aggregate --full
```

## Options

All command-line options override the settings in your `.aicodec/config.json` file.

-   **`-c, --config <PATH>`**: Specifies the path to the configuration file. **Default**: `.aicodec/config.json`.
-   **`-d, --directories <PATH...>`**: One or more root directories to scan for files. These paths can be absolute, relative to the current working directory, or relative to the project root (where `.aicodec/config.json` is located). Overrides the `directories` setting in the config.
-   **`-i, --include <PATTERN...>`**: One or more gitignore-style glob patterns to explicitly include. These rules override any exclusions.
-   **`-e, --exclude <PATTERN...>`**: One or more gitignore-style glob patterns to exclude.
-   **`--full`**: Performs a full aggregation, ignoring the cache of file hashes and including all files that match the criteria, regardless of whether they have changed.
-   **`--count-tokens`**: Counts the number of tokens in the final `context.json` output using the `cl100k_base` encoding (used by GPT-4) and displays it in the summary.
-   **`--plugin <PATTERN...>`**: Define a plugin on the fly, e.g., `".ext=command {file}"`. This overrides any plugins defined in `config.json` for the same file extension. For more details, see [Plugins](../guides/plugins.md).
-   **`--use-gitignore` / `--no-gitignore`**: A mutually exclusive pair of flags to explicitly enable or disable using the `.gitignore` file for exclusions.
