# AI Codec

AI Codec is a lightweight, CLI-first tool designed to streamline the interaction between a software developer and a Large Language Model (LLM). It provides a structured, reviewable, and reversible workflow for applying LLM-generated code changes to your project.

## Features

- **Interactive Project Setup**: Quickly initialize your project with `aicodec init`.
- **Flexible File Aggregation**: Gather all relevant project files into a single JSON context for the LLM, with powerful inclusion/exclusion rules.
- **Web-Based Visual Diff**: Review proposed changes in a clean, web-based diff viewer before they are applied to your file system.
- **Selective Application**: You have full control to select which files to modify, create, or delete from the LLM's proposal.
- **One-Click Revert**: Instantly revert the last set of applied changes with the `aicodec revert` command.
- **Clipboard Integration**: Pipe your LLM's response directly from your clipboard into the review process.

---

## Workflow and Usage

The `aicodec` workflow is designed to be simple and integrate cleanly with your existing development practices, including version control like Git.

### Step 1: Initialization

First, initialize `aicodec` in your project's root directory. You only need to do this once.

```bash
aicodec init
```

This command will guide you through an interactive setup to create a `.aicodec/config.json` file. This file tells `aicodec` which files to include or exclude when building context for the LLM.

### Step 2: Aggregating Context

Next, gather the code you want the LLM to work on.

```bash
aicodec aggregate
```

This command scans your project based on your configuration and creates a `context.json` file. This file contains the content of all relevant files, which you can now provide to your LLM.

### Step 3: Generating Changes with an LLM

Upload the content of `context.json` into your LLM of choice (or copy / paste it). Ask it to perform refactoring, add features, fix bugs etc. 

**Crucially, you must instruct the LLM to format its response as a JSON object that adheres to the tool's schema.** Here is an example of a valid response:

```json
{
  "summary": "Refactors the main function for clarity and adds error handling.",
  "changes": [
    {
      "filePath": "src/main.py",
      "action": "REPLACE",
      "content": "# New, refactored content of main.py..."
    },
    {
      "filePath": "src/utils.py",
      "action": "CREATE",
      "content": "# New utility functions..."
    }
  ]
}
```

### Step 4: Preparing to Apply Changes

Once you have the JSON output from the LLM, copy it to your clipboard.

Then, run the `prepare` command:

```bash
aicodec prepare --from-clipboard
```

This validates the JSON from your clipboard and saves it to `.aicodec/changes.json`, getting it ready for review.

Alternatively, you can run `aicodec prepare` without the flag to create an empty file and paste the content manually.

### Step 5: Reviewing and Applying Changes

This is the most important step. Run the `apply` command to launch the web-based review UI:

```bash
aicodec apply
```

Your browser will open a local web page showing a diff of all proposed changes. Here you can:
- Select or deselect individual changes.
- View a color-coded diff for each file.
- Edit the proposed changes directly in the UI.

Once you are satisfied, click **"Apply Selected Changes"**. The tool will modify your local files and create a `.aicodec/revert.json` file as a safety net.

### Step 6: Reverting Changes (The "Oops" Button)

If you are unhappy with the result of an `apply` operation, you can easily undo it.

```bash
aicodec revert
```

This command opens the same review UI, but this time it shows the changes required to restore your files to their state before the last `apply` operation. Select the changes you wish to undo and click **"Revert Selected Changes"**.