# `aicodec apply`

Launches a local web server and opens a browser-based UI to review, edit, and apply the proposed changes from the LLM.

This command is the core safety feature of AI Codec. It gives you full control to inspect and validate every change with a visual diff before any files on your system are modified.

## Prerequisites

This command requires a valid `.aicodec/changes.json` file, which is created by the `prepare` command.

## Usage

```bash
aicodec apply
```

## The Review UI

The web UI allows you to:
-   View a summary of the proposed changes.
-   See a list of all files to be created, modified, or deleted.
-   Select or deselect individual changes to be applied.
-   View a color-coded, side-by-side diff for each file.
-   **Directly edit** the LLM's proposed content in the diff viewer before applying.
-   Save your edits back to the `changes.json` file without applying them.

When you apply changes, the tool creates a `.aicodec/revert.json` file that allows the entire operation to be undone with the `revert` command.

## Options

-   **`-c, --config <PATH>`**: Specifies the path to the configuration file. **Default**: `.aicodec/config.json`.
-   **`-od, --output-dir <PATH>`**: The project directory where changes should be applied. Overrides the `output_dir` setting in the config.
-   **`--changes <PATH>`**: The path to the LLM changes JSON file to be reviewed. Overrides the `changes` path in the config.
