# `aicodec revert`

Launches the web UI to restore your files to their state *before* the last `aicodec apply` operation. This command acts as a safe and reliable "undo" button.

It uses the `.aicodec/revert.json` file that was automatically created during the `apply` step.

## Prerequisites

This command requires a `.aicodec/revert.json` file from a previous `apply` operation.

## Usage

```bash
# Launch the interactive revert UI
aicodec revert

# Revert all changes directly without the UI
aicodec revert --all
```

Just like `apply`, this command opens a review UI showing the changes needed to revert your files. You can selectively apply these reversions and must click the "Revert Selected Changes" button to confirm.

## Options

- 	**`-c, --config <PATH>`**: Specifies the path to the configuration file. **Default**: `.aicodec/config.json`.
- 	**`-od, --output-dir <PATH>`**: The project directory where changes should be reverted. This should be the same directory targeted by the `apply` command. Overrides the `output_dir` setting in the config.
- 	**`-a, --all`**: Reverts all changes from the last `apply` operation directly without launching the interactive review UI.
