# `aicodec prompt`

Generates a complete, ready-to-use prompt for an LLM. It combines a prompt template with your aggregated code context (`context.json`) and the required JSON output schema.

## Prerequisites

This command usually requires a `.aicodec/context.json` file, which is created by the `aggregate` command. You can run it without a context file by using the `--no-code` flag.

## Usage

```bash
aicodec prompt --task "Refactor the User class to use composition instead of inheritance."
```

## Options

-   **`-c, --config <PATH>`**: Specifies the path to the configuration file. **Default**: `.aicodec/config.json`.
-   **`--task "<YOUR TASK DESCRIPTION>"`**: The specific coding task you want the LLM to perform. This text is inserted into the prompt template.
-   **`--tech-stack "<YOUR TECH STACK>"`**: The primary language or tech stack for the LLM to consider.
-   **`--output-file <PATH>`**: Specifies where to save the generated prompt file. Overrides the `output_file` setting in the config.
-   **`--clipboard`**: Copies the generated prompt directly to the system clipboard instead of writing it to a file. Overrides the default behavior in the config.
-   **`--minimal`**: Uses a minimal prompt template. This reduces context size but may yield less reliable results from the LLM.
-   **`--no-code`**: Excludes the code context from `.aicodec/context.json` from the prompt. Useful for asking general questions.
