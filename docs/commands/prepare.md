# `aicodec prepare`

Prepares the LLM's JSON response for the review step. This command validates the JSON against the required schema and saves it to the changes file (by default, `.aicodec/changes.json`).

## Usage

```bash
aicodec prepare [OPTIONS]
```

This command can operate in two modes:

1.  **From Clipboard**: Reads content directly from your clipboard, validates it, and saves it.
2.  **Editor Mode**: Creates an empty changes file and opens it in your default text editor for you to paste the JSON into.

## Options

-   **`-c, --config <PATH>`**: Specifies the path to the configuration file. **Default**: `.aicodec/config.json`.
-   **`--changes <PATH>`**: The path where the validated LLM changes will be saved. Overrides the `changes` path in the config.
-   **`--from-clipboard`**: Use this flag to read the LLM's JSON response directly from the system clipboard. This overrides the default behavior set in your config.
