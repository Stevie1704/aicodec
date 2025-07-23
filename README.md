# AI Codec: Lightweight AI Coding Assistant Toolkit

AI Codec is a toolkit designed to streamline the process of interacting with Large Language Models (LLMs) for code generation and modification. It provides a structured, reliable, and efficient way to package your local codebase for an LLM and then automatically apply its suggested changes back to your project. No need for an API key, just put the structured json in the LLM's chat window of your choice and get started.

## The Problem

When working with LLMs, developers often face two major challenges:

1. **Context Stuffing:** Manually copying and pasting relevant files into a prompt is tedious and quickly hits the model's context window limit.

2. **Applying Changes:** Manually transferring code modifications from the LLM's response back into your local files is slow, error-prone, and doesn't scale.

This toolkit solves these problems with two specialized command-line tools: an **encoder** (`ai-encode`) and a **decoder** (`ai-decode`).

## Why Use AI Codec?

While many sophisticated AI coding tools exist (see last chapter), AI Codec's strength lies in its **simplicity and transparency**.

* **Full Control:** You have complete control over the process. You see the exact JSON context being sent to the LLM and the exact JSON changes being returned before they are applied. There are no hidden steps.

* **Decoupled Workflow:** The encoder and decoder are separate commands. This allows for an asynchronous workflow where you can generate context, get feedback, and apply changes at your own pace.

* **Simplicity and Portability:** It's a simple Python package with minimal dependencies. It's easy to understand, modify, and run anywhere you have Python, without needing to install a complex IDE or plugin.

## Workflow

The end-to-end workflow is simple and powerful:

1. **Encode:** Use the `ai-encode` command to scan your project, select only the relevant source files, and package them into a single `context.json` file.

2. **Interact:** Share the contents of `context.json` with your LLM. Ask it to perform a task and request that it provides the response in the specified JSON patch format.

3. **Decode:** Save the LLM's JSON response as `changes.json` and use the `ai-decode` command to validate and automatically apply the proposed modifications to your project directory.

## Installation

1. Clone this repository.

2. Navigate to the repository root and install the package in editable mode. This will also install dependencies like `jsonschema` and make the command-line tools available.

   ```bash
   pip install -e .
   ```

3. To install the dependencies required for running tests, use:

   ```bash
   pip install -e ".[dev]"
   ```

## Usage

### Configuration File

For the best experience, create a `.aicodec-config.json` file in your project root. This allows you to run both `ai-encode` and `ai-decode` without any command-line arguments.

**Example `.aicodec-config.json`:**
```json
{
    "encoder": {
        "ext": [
            ".py",
            ".toml",
            ".md"
        ],
        "file": ["Dockerfile"],
        "output": "project_context.json",
        "exclude_dirs": [
            ".git",
            "__pycache__",
            "dist",
            "build",
            ".pytest_cache"
        ]
    },
    "decoder": {
        "input": "llm-changes.json",
        "output_dir": "."
    }
}
```

### 1. `ai-encode` (The Encoder)

With the configuration file in place, you can simply run:
```bash
ai-encode
```
Alternatively, you can override any setting using command-line arguments:
```bash
ai-encode --ext .py --output my_project.json
```

### 2. `ai-decode` (The Decoder)

With the configuration file in place, you can simply run:
```bash
ai-decode
```
To perform a dry run first, use the `--dry-run` flag:
```bash
ai-decode --dry-run
```

## Running Tests

This project uses `pytest`. To run the test suite, navigate to the project root and run:

```bash
pytest
```

## Interacting with the LLM

### Example Prompt

To get a high-quality response from your LLM, you need to be explicit. Here is a template you can use:

> **User Prompt:**
>
> Please act as a senior Python software engineer. Your task is to modify the following codebase based on my request. Your response should be well-structured, adhere to best practices, and be ready for production use.
>
> Here is the context for the entire project in a JSON format:
> ```json
> [PASTE THE CONTENT OF YOUR `project_context.json` HERE]
> ```
>
> **My request is:** Please add a new function in `src/utils.py` called `hello_world` that prints "Hello, World!".
>
> **IMPORTANT:** Your response must be a JSON object that validates against the following schema. Provide only the raw JSON object and nothing else.
>
> ```json
> {
>   "$schema": "[http://json-schema.org/draft-07/schema#](http://json-schema.org/draft-07/schema#)",
>   "title": "LLM Code Change Proposal",
>   "type": "object",
>   "properties": {
>     "summary": { "type": "string" },
>     "changes": {
>       "type": "array",
>       "items": {
>         "type": "object",
>         "properties": {
>           "filePath": { "type": "string" },
>           "action": { "type": "string", "enum": ["REPLACE", "CREATE"] },
>           "content": { "type": "string" }
>         },
>         "required": ["filePath", "action", "content"]
>       }
>     }
>   },
>   "required": ["changes"]
> }
> ```

## Related Projects

If you are looking for more advanced, integrated solutions that combine these steps into a single tool, consider checking out these excellent open-source projects:

* [**Aider**](https://github.com/paul-gauthier/aider): A popular command-line chat tool that lets you code with an LLM right in your terminal. It handles file management and applies changes automatically.

* **[Mentat](https://github.com/AbanteAI/mentat)**: Another powerful terminal-based AI coding assistant that can edit code across multiple files based on your instructions.

* **[Cursor](https://cursor.sh/)**: An AI-native code editor (a fork of VS Code) that deeply integrates LLM features for code generation, editing, and debugging.