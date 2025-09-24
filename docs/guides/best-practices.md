# Best Practices & Tips

To get the most out of `aicodec`, follow these best practices for context management, prompting, and workflow integration.

---

### 1. Craft Specific and Actionable Tasks

The quality of the LLM's output depends heavily on the quality of your input.

-   **Be Specific:** Instead of "fix the bug," describe the bug and the expected behavior. "The `add` function fails on negative numbers. Modify it to correctly handle them and add a new test case for `add(-2, -3)`."
-   **Be Atomic:** Ask for one logical change at a time. It's better to run the workflow twice for two separate features than to ask for a huge, complex change in one prompt. This makes reviewing easier and reduces the chance of LLM errors.
-   **Specify File Names:** If you want a new file created, tell the LLM its exact name and path (e.g., `src/utils/new_helper.py`).

---

### 2. Manage Your Context Carefully

The `context.json` file is your primary tool for focusing the LLM's attention. A smaller, more relevant context leads to faster, cheaper, and more accurate responses.

-   **Start with Defaults:** The default configuration (using `.gitignore`) is often a great starting point.
-   **Use `include_` Rules for Focus:** If you're only working on your API layer, use `"include_dirs": ["src/api"]` in your `config.json` to temporarily focus the context.
-   **Exclude Noise:** Aggressively exclude directories and files that are never relevant, such as build artifacts, documentation, or large data assets.
-   **Use `--full` Sparingly:** The default incremental aggregation (only adding changed files) is efficient. Only use `aicodec aggregate --full` when you've made significant changes to your configuration or need to give the LLM a complete picture of the project from scratch.

---

### 3. Leverage the Review UI

The web UI is your most important safety net. Don't just blindly click "Apply."

-   **Review Every Diff:** Carefully check each change. LLMs can sometimes make subtle mistakes, introduce typos, or remove important code.
-   **Use the Live Editor:** Did the LLM almost get it right but miss a semicolon or a variable name? Don't reject the whole change. **Click into the right-hand panel of the diff viewer and fix it directly.** You can then save your edits back to `changes.json` or apply them immediately.
-   **Apply Selectively:** If an LLM proposes five changes but only three are good, uncheck the bad ones and apply the rest. You can then run a new prompt to fix the remaining issues.

---

### 4. Integrate with Version Control

`aicodec` is designed to complement `git`, not replace it.

-   **Always Work on a Branch:** Before starting the `aicodec` workflow, create a new git branch (`git checkout -b feature/llm-refactor`). This isolates the AI-generated changes.
-   **Review Before Committing:** After a successful `aicodec apply`, use `git status` and `git diff` as a final sanity check before you `git add` and `git commit`.
-   **Use `revert` for a Clean Slate:** If you're unhappy with the applied changes, `aicodec revert` will restore your files. `git status` should then show a clean working directory, and you can safely delete your feature branch.
