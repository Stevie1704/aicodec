# `aicodec init`

Initializes `aicodec` in your project's root directory.

This command runs an interactive wizard that guides you through creating a `.aicodec/config.json` file. You only need to run this once per project.

## Usage

```bash
aicodec init
```

The wizard will ask a series of questions to configure the core components of the tool.

### Configuration Steps

1.  **File Aggregation**: Set rules for which files and directories to include or exclude when creating the context for the LLM.
2.  **Gitignore Usage**: Choose whether to respect your project's `.gitignore` file and whether `aicodec` should add its own `.aicodec/` directory to it (recommended).
3.  **LLM Interaction**: Set default behaviors for handling prompts and LLM responses, such as reading from or writing to the system clipboard.
4.  **Tech Stack**: Optionally provide information about your project's language or framework to improve the LLM's context.

For a detailed breakdown of every available option, see the **[Configuration Reference](../configuration.md)**.

## Options

This command has no command-line options as it is fully interactive. If a `.aicodec/config.json` file already exists, it will ask for confirmation before overwriting it.
