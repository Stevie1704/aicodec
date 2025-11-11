# Plugins

`aicodec`'s plugin system allows you to extend its capabilities by integrating external scripts to process and "decode" binary or complex file formats into a text-based representation that can be understood by an LLM. This is particularly useful for including information from files like `.zip` archives, `.hdf5` datasets, or proprietary formats that `aicodec` wouldn't natively understand.

## How Plugins Work

When `aicodec aggregate` encounters a file with an extension for which a plugin is defined, it will:

1.  Execute the specified external script, passing the absolute path of the file as an argument.
2.  Capture the standard output (stdout) of the script.
3.  Use this stdout as the "content" of the file when building the `context.json` for the LLM.

This allows you to transform complex data into a human-readable (and LLM-readable) format, such as a summary, a data tree, or a description.

## Defining Plugins

Plugins can be defined in two ways:

### 1. In `config.json` (Recommended for Project-Wide Use)

You can specify plugins in the `aggregate` section of your `.aicodec/config.json` file. This is ideal for plugins that are part of your project's standard workflow.

```json
{
  "aggregate": {
    "directories": ["."],
    "use_gitignore": true,
    "plugins": [
      ".zip=./scripts/decode_zip.sh {file}",
      ".h5=python scripts/hdf5_summary.py --path {file}"
    ]
  }
}
```

Each entry in the `plugins` list is a string in the format `".ext=command {file}"`:

*   `".ext"`: The file extension (including the dot) that this plugin should handle (e.g., `.zip`, `.h5`).
*   `"command {file}"`: The command to execute. The placeholder `{file}` will be replaced by the absolute path of the file being processed.

### 2. Via Command-Line Argument (For Temporary or One-Off Use)

You can also define plugins directly when running the `aicodec aggregate` or `aicodec init` commands using the `--plugin` flag. Command-line plugins will override any plugins defined in `config.json` for the same file extension.

```bash
aicodec aggregate --plugin ".zip=./scripts/decode_zip.sh {file}"
```

You can specify multiple plugins by repeating the `--plugin` flag:

```bash
aicodec aggregate \
  --plugin ".zip=./scripts/decode_zip.sh {file}" \
  --plugin ".tar.gz=tar -ztvf {file}"
```

## Important Considerations

*   **`shell=False`**: Plugin commands are executed with `shell=False` for security reasons. This means you cannot use shell-specific features like pipes (`|`), redirection (`>`), or environment variable expansion (`$VAR`) directly within the `command` string. If your plugin logic requires these features, you should wrap your command in a separate shell script and call that script as your plugin.
*   **Output Format**: The output of your plugin script (to stdout) will be used directly as the content for the LLM. While any string format is accepted (plain text, Markdown, JSON, etc.), it's recommended to output content that is easily digestible and informative for an LLM.
*   **Error Handling**: Your plugin script should handle errors gracefully. If the script exits with a non-zero status code, `aicodec` will log a warning and skip the file.

## Example: Decoding a ZIP File

Let's walk through an example of creating a plugin to list the contents of a `.zip` file.

### 1. Create a Test File and a ZIP Archive

First, create a directory for your test and make a simple ZIP file.

```bash
# Create a directory and move into it
mkdir plugin_test
cd plugin_test

# Create a dummy file
echo "hello world" > my_text_file.txt

# Create a ZIP archive containing the file
zip test.zip my_text_file.txt
```

You now have a binary file named `test.zip`.

### 2. Create the Decoder Plugin Script

Next, create a small shell script that will act as our plugin. This script will take a file path as an argument and use the standard `unzip -l` command to list its contents.

Create a file named `decode_zip.sh` in your `plugin_test` directory and put the following content in it:

```sh
#!/bin/sh
# decode_zip.sh

# This script lists the contents of a zip file.
# The first argument ($1) is the path to the file.
unzip -l "$1"
```

Make the script executable:

```bash
chmod +x decode_zip.sh
```

### 3. Run `aicodec aggregate` with the Plugin

Now, you can run the `aggregate` command and tell it to use your `decode_zip.sh` script for any file ending in `.zip`. We'll use the `--plugin` command-line argument.

Execute the following command in your `plugin_test` directory:

```bash
aicodec aggregate --plugin ".zip=./decode_zip.sh {file}" --include "*.zip"
```

*   `--plugin ".zip=./decode_zip.sh {file}"`: This registers your script as a plugin for `.zip` files.
*   `--include "*.zip"`: This tells `aicodec` to specifically include `.zip` files in its scan.

### 4. Check the Output

After running the command, a file named `.aicodec/context.json` will be created. Its content will look something like this:

```json
[
  {
    "filePath": "test.zip",
    "content": "Archive:  test.zip\nLength      Date    Time    Name\n---------  ---------- -----   ----
       12  2025-11-11 18:45   my_text_file.txt\n---------          -------
       12                  1 file\n"
  }
]
```

As you can see, the `content` for `test.zip` is not the binary zip data, but the human-readable text output from your `decode_zip.sh` plugin. This demonstrates that the plugin system is working as designed.
