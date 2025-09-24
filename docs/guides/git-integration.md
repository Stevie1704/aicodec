# Git Integration

`aicodec` is designed to work seamlessly with version control systems like Git. By combining `aicodec` with a good Git workflow, you can experiment with LLM-generated code safely and maintain a clean, professional commit history.

---

## Recommended Workflow

Here is the recommended workflow for using `aicodec` in a project managed with Git.

### 1. Start on a Clean Branch

Before you begin, ensure your `main` branch is clean and up-to-date. Then, create a new feature branch for the changes you plan to make.

```bash
# Make sure you're on the main branch and have the latest changes
git checkout main
git pull origin main

# Create a new branch for your task
git checkout -b feature/add-user-authentication
```
Working on a dedicated branch isolates the AI-generated changes, making them easy to discard if they don't work out.

### 2. Run the AI Codec Cycle

Now, perform the standard `aicodec` workflow on your new branch:

1.  `aicodec aggregate`
2.  `aicodec prompt --task "..."`
3.  (Get JSON response from LLM)
4.  `aicodec prepare --from-clipboard`
5.  `aicodec apply`

### 3. Review Changes in Git

After the `apply` command has finished, your files have been modified. `aicodec` has done its job, and now Git takes over.

Use standard Git commands to review the state of your working directory:

```bash
# See which files were created, modified, or deleted
git status

# Review the exact line-by-line changes
git diff

# Or review changes for a specific file
git diff src/models/user.py
```

This serves as a final, crucial sanity check.

### 4. Commit or Revert

You now have two main options:

**A) If you are happy with the changes:**

Commit them to your feature branch with a clear message.

```bash
git add .
git commit -m "feat: Add user model and authentication service via LLM"
```
You can now continue working, push the branch, and open a pull request as you normally would.

**B) If you are NOT happy with the changes:**

Use the `aicodec revert` command to undo the operation.

```bash
aicodec revert
```

After the revert is complete, your working directory will be restored to its state before you ran `aicodec apply`. You can confirm this with `git status`, which should show no changes.

```bash
git status
# On branch feature/add-user-authentication
# nothing to commit, working tree clean
```

Your branch is now in a clean state, and you can either abandon it (`git checkout main && git branch -D feature/add-user-authentication`) or try a different prompt with the LLM.

---

## The `.gitignore` File

The `aicodec init` command will offer to add the `.aicodec/` directory to your `.gitignore` file. It is **highly recommended** that you do this.

The files within this directory (`config.json`, `context.json`, `changes.json`, etc.) are specific to your local workflow and should not be committed to your project's history.
