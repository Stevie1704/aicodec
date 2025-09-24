# Getting Started: A Step-by-Step Tutorial

This guide will walk you through a complete `aicodec` workflow, from initializing a project to applying and reverting an LLM-generated change.

**Our Goal:** We'll start with a simple Python project containing a single function. We'll then ask an LLM to add a new function and a unit test for it.

---

### Step 0: Project Setup

First, let's create a simple project to work with.

1.  Create a new directory and `cd` into it:
    ```bash
    mkdir my-python-project
    cd my-python-project
    ```

2.  Create a file named `calculator.py` with this content:
    ```python
    # calculator.py
    def add(a, b):
        """Adds two numbers together."""
        return a + b
    ```

Your project now has one file.

---

### Step 1: Initialize AI Codec

Run the `init` command in your project's root directory. This creates the `.aicodec/config.json` file that powers the tool.

```bash
aicodec init
```

The interactive wizard will ask you a few questions. For this tutorial, you can accept the defaults for most prompts by pressing `Enter`.

-   Use `.gitignore`? **Yes**
-   Update `.gitignore`? **Yes**
-   Configure additional inclusions/exclusions? **No**
-   Use minimal prompt? **No**
-   Primary tech stack? **python**
-   Read from clipboard by default (`prepare`)? **Yes**
-   Include code by default (`prompt`)? **Yes**
-   Copy prompt to clipboard by default? **Yes**

This will create a `.aicodec` directory and a `config.json` file inside it.

---

### Step 2: Aggregate Code for Context

Next, we need to gather our project's code into a single file that we can give to the LLM.

```bash
aicodec aggregate
```

This command reads your `config.json`, finds all relevant files (`calculator.py` in this case), and creates a `.aicodec/context.json` file. The output will look something like this:

```
Successfully aggregated 1 changed file(s) into '.aicodec/context.json'.
```

---

### Step 3: Generate the Prompt

Now, let's create the prompt for the LLM. We'll define our task using the `--task` flag.

```bash
aicodec prompt --task "Add a new function 'subtract(a, b)' to the calculator. Also, create a new file named 'test_calculator.py' with a pytest unit test for the new subtract function."
```

This generates a prompt containing the instructions, your code context, and the required JSON schema. It's in your clipboard (by configuration).

---

### Step 4: Interact with the LLM

1.  Paste the prompt into your favorite LLM chat interface (ChatGPT, Claude, etc.).
2.  The LLM will process the request and generate a JSON object as a response.

A valid response for our task would look like this:
```json
{
  "summary": "Adds a 'subtract' function and a corresponding unit test.",
  "changes": [
    {
      "filePath": "calculator.py",
      "action": "REPLACE",
      "content": "# calculator.py\ndef add(a, b):\n    \"\"\"Adds two numbers together.\"\"\"\n    return a + b\n\ndef subtract(a, b):\n    \"\"\"Subtracts b from a.\"\"\"\n    return a - b\n"
    },
    {
      "filePath": "test_calculator.py",
      "action": "CREATE",
      "content": "# test_calculator.py\nfrom calculator import subtract\n\ndef test_subtract():\n    assert subtract(5, 3) == 2\n    assert subtract(10, 10) == 0\n"
    }
  ]
}
```

5.  **Copy the raw JSON object** from the LLM's response to your clipboard.

---

### Step 5: Prepare the Changes

Now, feed the LLM's response into `aicodec`. Since we configured "from clipboard" as the default, this is simple:

```bash
aicodec prepare
```

This command validates the JSON from your clipboard against the schema and saves it to `.aicodec/changes.json`.

---

### Step 6: Review and Apply

This is the most important step. Let's launch the review UI:

```bash
aicodec apply
```

Your web browser will open a local page showing a diff of the proposed changes.

-   On the left, you'll see a list of files to be changed (`calculator.py` and `test_calculator.py`).
-   You can click on each file to see a color-coded diff.
-   You can even **edit the code directly in the right-hand panel** if the LLM made a small mistake.
-   Ensure both changes are checked, and then click the **"Apply Selected Changes"** button.

Once applied, check your file system. You'll see that `calculator.py` is updated and `test_calculator.py` has been created! The tool also creates a `.aicodec/revert.json` file as a safety net.

---

### Step 7: Revert the Changes (The "Undo" Button)

Made a mistake? Don't like the changes? No problem.

```bash
aicodec revert
```

The same review UI will open, but this time it shows the inverse operation: modifying `calculator.py` back to its original state and deleting `test_calculator.py`.

Click **"Revert Selected Changes"**. Your project is now back to exactly how it was before Step 6.

**Congratulations! You've completed the entire AI Codec workflow.**
