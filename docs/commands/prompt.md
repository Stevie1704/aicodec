# `aicodec prompt`

Generates a complete, ready-to-use prompt for an LLM. It combines a prompt template with your aggregated code context (`context.json`) and the required JSON output schema.

## Prerequisites

This command usually requires a `.aicodec/context.json` file, which is created by the `aggregate` command. You can run it without a context file by using the `--no-code` or `--new-project` flag.

## Usage

```bash
# Generate a prompt for a refactoring task
aicodec prompt --task "Refactor the User class to use composition instead of inheritance."

# Generate a prompt for a new project, which excludes code context
aicodec prompt --new-project --task "Create a simple FastAPI application with a single endpoint '/hello' that returns a JSON object."
```

## Options

-   **`-c, --config <PATH>`**: Specifies the path to the configuration file. **Default**: `.aicodec/config.json`.
-   **`--task "<YOUR TASK DESCRIPTION>"`**: The specific coding task you want the LLM to perform. This text is inserted into the prompt template.
-   **`--tech-stack "<YOUR TECH STACK>"`**: The primary language or tech stack for the LLM to consider.
-   **`--output-file <PATH>`**: Specifies where to save the generated prompt file. Overrides the `output_file` setting in the config.
-   **`--clipboard`**: Copies the generated prompt directly to the system clipboard instead of writing it to a file. Overrides the default behavior in the config.
-   **`--minimal`**: Uses a minimal prompt template. This reduces context size but may yield less reliable results from the LLM.
-   **`--no-code`**: Excludes the code context from `.aicodec/context.json` from the prompt. Useful for asking general questions or when the context is not relevant.
-   **`-noi`, `--no-output-instruction`**: Excludes the entire block for the output instructions from the prompt. This is useful when you want to have a feedback to your code base or provide custom output instructions directly in your task description.
-   **`-np`, `--new-project`**: Optimizes the prompt for generating a new project from scratch. It adjusts the task wording and automatically implies `--no-code`.
