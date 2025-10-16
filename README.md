# AI Codec

[![PyPI version](https://img.shields.io/pypi/v/aicodec)](https://pypi.org/project/aicodec/)
[![CI](https://github.com/Stevie1704/aicodec/actions/workflows/ci.yml/badge.svg)](https://github.com/Stevie1704/aicodec/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AI Codec is a lightweight, CLI-first tool that brings a structured, reviewable, and reversible workflow to applying LLM-generated code to your projects. Instead of chaotic copy-pasting from a chatbot, you get a formal, git-like review process for AI-driven changes.



---

## 📖 Full Documentation

**For a complete guide, including installation options, a step-by-step tutorial, and the full command reference, please visit the official documentation website:**

### **[https://stevie1704.github.io/aicodec/](https://stevie1704.github.io/aicodec/)**

---

## ✨ Features

-   **Structured Interaction**: Enforces a simple JSON schema, turning raw LLM output into a structured set of changes.
-   **Safe Review Process**: The `aicodec apply` command launches a web UI with a git-like diffing experience so you can see exactly what will change *before* any files are touched.
-   **Developer in Control**: Selectively apply, reject, or even edit the LLM's suggestions live in the diff viewer.
-   **Atomic & Reversible Changes**: The `apply` and `revert` commands make applying LLM suggestions a safe transaction that you can undo with a single command.
-   **Flexible File Aggregation**: Gather relevant project files into a single context for the LLM with powerful inclusion/exclusion rules.
-   **Clipboard Integration**: Pipe your LLM's response directly from your clipboard into the review process.
