# `aicodec buildmap`

Scans your project and generates a Markdown file (`.aicodec/repo_map.md`) containing a tree-like representation of your project's structure.

This command is designed to provide a high-level overview of the repository for an LLM. It is separate from `aicodec aggregate` to allow you to generate a complete map of your project while creating a focused content context with `aggregate`.

The `buildmap` command respects your project's `.gitignore` file by default but intentionally ignores the `include` and `exclude` rules from your `.aicodec/config.json` to ensure the map is comprehensive.

## Usage

```bash
# Build the repository map, respecting .gitignore
aicodec buildmap

# Build the map without using .gitignore
aicodec buildmap --no-gitignore
```

## Options

-   **`-c, --config <PATH>`**: Specifies the path to the configuration file. **Default**: `.aicodec/config.json`.
-   **`--use-gitignore` / `--no-gitignore`**: A mutually exclusive pair of flags to explicitly enable or disable using the `.gitignore` file for exclusions. The default is to use it.
