# AI Codec

AI Codec is a lightweight, CLI-first tool designed to streamline the interaction between a software developer and a Large Language Model (LLM). It provides a structured, reviewable, and reversible workflow for applying LLM-generated code changes to your project.

It’s designed for the developer who:
* Prefers interacting directly with an LLM's web chat window.
* Wants to avoid the complexity and cost of managing API keys.
* Is not using a fully-integrated solution like Aider and wants a structured way to apply code.

## The Problem

LLMs are incredibly powerful for generating code, but integrating their suggestions into a project is often a messy, manual process. Developers typically face:

- **Unstructured Output**: LLMs produce large, unstructured blocks of code that are difficult to parse.
- **Tedious Manual Work**: Manually copying and pasting changes across multiple files is slow and highly prone to error.
- **Difficult Reviews**: It's hard to see a clear "diff" of the proposed changes before applying them, losing the safety of a code review process.
- **No Easy Undo**: If an applied change introduces a bug, there is no simple, one-step process to revert the file system to its previous state.

## Why Use AI Codec?

AI Codec solves these problems by treating LLM-generated changes as a formal, reviewable patch, much like a pull request.

- **Structured Interaction**: It enforces a simple JSON schema, turning the LLM's raw output into a structured set of changes.
- **Safe Review Process**: The `aicodec apply` command launches a web UI that provides a git-like diffing experience, so you can see exactly what will change *before* any files are touched.
- **Developer in Control**: You have the final say. Selectively apply or reject any change, or even edit the LLM's suggestions live in the diff viewer.
- **Atomic & Reversible Changes**: The `apply` and `revert` commands make applying LLM suggestions a safe, atomic transaction that you can undo with a single command.

## Features

- **Interactive Project Setup**: Quickly initialize your project with `aicodec init`.
- **Flexible File Aggregation**: Gather all relevant project files into a single JSON context for the LLM, with powerful inclusion/exclusion rules.
- **Web-Based Visual Diff**: Review proposed changes in a clean, web-based diff viewer before they are applied to your file system.
- **Selective Application**: You have full control to select which files to modify, create, or delete from the LLM's proposal.
- **One-Click Revert**: Instantly revert the last set of applied changes with the `aicodec revert` command.
- **Clipboard Integration**: Pipe your LLM's response directly from your clipboard into the review process.
- **Built-in Schema Access**: Easily access the required JSON schema with the `aicodec schema` command.

---

## Installation

Aicodec is available on PyPi.

```bash
pip install aicodec 
```

This will make the `aicodec` command available in your terminal.

## Workflow and Usage

The `aicodec` workflow is designed to be simple and integrate cleanly with your existing development practices, including version control like Git.

### Step 1: Initialization

First, initialize `aicodec` in your project's root directory. You only need to do this once.

```bash
aicodec init
```

This command will guide you through an interactive setup to create a `.aicodec/config.json` file.

### Step 2: Aggregating Context

Next, gather the code you want the LLM to work on.

```bash
aicodec aggregate
```

This command scans your project based on your configuration and creates a `context.json` file. This file contains the content of all relevant files, which you can now provide to your LLM.

### Step 3: Generating the Prompt

Run the `prompt` command to generate a ready-to-use prompt file that includes your aggregated context:

```bash
aicodec prompt
```

This will create a `prompt.txt` file in your `.aicodec` directory (configurable). You can customize the task with `--task "your description"` or copy directly to clipboard with `--clipboard`.

### Step 4: Generating Changes with an LLM

Copy the contents of `prompt.txt` (if not already in your clipboard) and paste it into your LLM of choice. Ask it to perform refactoring, add features, or fix bugs. 

**Crucially, you must instruct the LLM to format its response as a JSON object that adheres to the tool's schema.**

You can then provide this schema to the LLM along with your project context and prompt.

### Step 5: Preparing to Apply Changes

Once you have the JSON output from the LLM, copy it to your clipboard.

Then, run the `prepare` command:

```bash
aicodec prepare --from-clipboard
```

This validates the JSON from your clipboard and saves it to `.aicodec/changes.json`, getting it ready for review.
You can also configure it as default flag in your config by adding under "prepare" the "from-clipboar": true option.

### Step 6: Reviewing and Applying Changes

This is the most important step. Run the `apply` command to launch the web-based review UI:

```bash
aicodec apply
```

Your browser will open a local web page showing a diff of all proposed changes. Here you can:
- Select or deselect individual changes.
- View a color-coded diff for each file.
- Edit the proposed changes directly in the UI.

Once you are satisfied, click **"Apply Selected Changes"**. The tool will modify your local files and create a `.aicodec/revert.json` file as a safety net.

### Step 7: Reverting Changes (The "Oops" Button)

If you are unhappy with the result of an `apply` operation, you can easily undo it.

```bash
aicodec revert
```

This command opens the same review UI, but this time it shows the changes required to restore your files to their state before the last `apply` operation.

## Additional commands
### Get schema
To get the required schema, which the llm needs to follow, run the following command in your terminal:

```bash
aicodec schema
```

You can directly pipe this output to your clip by e.g. using `aicodec schema | pbcopy` on macOS, `| clip` on Windows, or `| xclip` on Linux.