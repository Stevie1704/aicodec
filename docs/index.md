# AI Codec Documentation

**AI Codec is a lightweight, CLI-first tool that brings a structured, reviewable, and reversible workflow to applying LLM-generated code to your projects.**

In an era of increasingly complex agentic coding systems, AI Codec embraces a simpler, more direct approach. Interacting with an LLM in a chat window is a powerful and flexible workflow that many developers prefer, but it lacks a safe bridge to the local filesystem. This tool provides that bridge.

It acts as a safe, sane link between your local development environment and the raw power of Large Language Models. Instead of chaotic copy-pasting, you get a formal, git-like review process for AI-driven changes.

## The Problem with Manual AI Integration

Integrating LLM suggestions into a project is often a messy, manual process. You face:

- 	 **Unstructured Output**: Raw code blocks from a chatbot are hard to parse and apply across multiple files.
- 	 **Tedious Copy-Pasting**: Manually transferring code is slow, error-prone, and painful.
- 	 **No Safety Net**: There's no clear diff to review before changes hit your file system, and no easy "undo" button if things go wrong.

## The AI Codec Solution

AI Codec solves these problems by treating LLM-generated changes as a formal, reviewable patch, much like a pull request.

- 	 **🤖 Structured Interaction**: Enforces a simple JSON schema, turning the LLM's output into a structured set of file operations.
- 	 **🧐 Safe Review Process**: The `aicodec apply` command launches a web UI with a git-like diffing experience. You see exactly what will change *before* any files are touched.
- 	 **✅ Developer in Control**: You have the final say. Selectively apply, reject, or even edit the LLM's suggestions live in the diff viewer.
- 	 **⏪ Atomic & Reversible Changes**: The `apply` and `revert` commands make applying LLM suggestions a safe transaction that you can undo with a single command.

## Who Is This For?

AI Codec is designed for the developer who:

- 	 Prefers the flexibility of interacting directly with an LLM's web interface (like ChatGPT, Claude, Gemini, etc.).
- 	 Wants to avoid the complexity and cost of managing API keys.
- 	 Needs a structured, safe, and reversible way to apply AI-generated code without the overhead of a fully integrated solution like Aider.

---

## Next Steps

- 	 **🚀 Ready to start?** Jump into the **[Getting Started](./getting-started/installation.md)** guide for a full walkthrough.
- 	 **⚙️ Want to customize?** Learn about all the options in the **[Configuration](./configuration.md)** reference.
