# `aicodec schema`

Prints the required JSON schema to standard output.

This schema defines the exact structure that an LLM's response must follow to be considered valid by `aicodec prepare`. You should include this schema in your prompt to the LLM to ensure it generates a valid response.

## Usage

```bash
aicodec schema
```

You can easily pipe this output to your clipboard for use in your prompt:

-   **macOS**: `aicodec schema | pbcopy`
-   **Windows**: `aicodec schema | clip`
-   **Linux (with xclip)**: `aicodec schema | xclip -selection clipboard`

## Options

This command has no command-line options.
