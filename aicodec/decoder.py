import os
import argparse
import json
import jsonschema


def apply_changes(changes_data, output_dir, dry_run=False, auto_confirm=False):
    """
    Applies file changes described in the provided data structure into a
    specified output directory.

    Args:
        changes_data (dict): The parsed and validated JSON data.
        output_dir (str): The root directory where changes will be applied.
        dry_run (bool): If True, only print what would be done.
        auto_confirm (bool): If True, bypass the confirmation prompt.
    """
    changes = changes_data['changes']

    print(f"Proposed changes will be applied to directory: {output_dir}\n")
    print("The following changes are proposed:")
    for change in changes:
        action = change.get('action', 'UNKNOWN')
        # Show the final path for clarity
        final_path = os.path.join(output_dir, change.get('filePath', 'N/A'))
        print(f"- {action}: {final_path}")

    if dry_run:
        print("\nDry run complete. No files were changed.")
        return

    if not auto_confirm:
        try:
            confirm = input("\nDo you want to apply these changes? [y/N]: ")
            if confirm.lower().strip() != 'y':
                print("Operation cancelled.")
                return
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return

    print("\nApplying changes...")
    for change in changes:
        action = change.get('action')
        relative_path = change.get('filePath')
        content = change.get('content')

        # Construct the full, absolute path for the file operation.
        target_path = os.path.join(output_dir, relative_path)

        if action.upper() in ['REPLACE', 'CREATE']:
            try:
                # Ensure the directory for the file exists.
                parent_dir = os.path.dirname(target_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)

                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"SUCCESS: Replaced/Created {target_path}")

            except Exception as e:
                print(f"FAILURE: Could not write to file {target_path}: {e}")
        else:
            print(
                f"WARNING: Action '{action}' is not supported. Skipping {relative_path}.")

    print("\nAll changes applied.")


def load_config(config_path):
    """Loads configuration from a JSON file if it exists."""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def main():
    """
    Parses arguments, validates the input file against a schema,
    and initiates the decoding process.
    """
    parser = argparse.ArgumentParser(
        description="Validates and applies code changes from a JSON file to a target directory."
    )

    parser.add_argument(
        '-c', '--config',
        type=str,
        default='.aicodec-config.json',
        help="Path to the configuration file."
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        help="Path to the input JSON file containing the changes."
    )
    parser.add_argument(
        '-od', '--output-dir',
        type=str,
        help="The directory where files will be created/updated."
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show changes without applying them."
    )
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help="Automatically confirm and apply changes."
    )

    args = parser.parse_args()

    # --- Configuration Loading and Merging ---
    full_config = load_config(args.config)
    decoder_config = full_config.get('decoder', {})

    # Determine settings with priority: CLI argument > config file
    input_file = args.input or decoder_config.get('input')
    output_directory = args.output_dir or decoder_config.get('output_dir')

    # Validate that we have an input file
    if not input_file:
        parser.error(
            "No input file specified. Provide it via the --input argument or in the 'decoder' section of your config file.")

    # Handle default for output_directory if not specified anywhere
    if not output_directory:
        output_directory = os.path.dirname(os.path.abspath(input_file))

    # --- Load Data and Schema ---
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(script_dir, 'decoder_schema.json')

        with open(input_file, 'r', encoding='utf-8') as f:
            data_to_validate = json.load(f)
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: Could not find a required file. {e}")
        return
    except json.JSONDecodeError as e:
        print(
            f"Error: Could not decode JSON from {input_file}. Please check the format. {e}")
        return

    # --- Validate against Schema ---
    try:
        jsonschema.validate(instance=data_to_validate, schema=schema)
        print("JSON data is valid against the schema.")
    except jsonschema.exceptions.ValidationError as e:
        print("JSON validation failed!")
        print(f"Error: {e.message}")
        print(f"On instance: {e.instance}")
        return
    except Exception as e:
        print(f"An unexpected error occurred during validation: {e}")
        return

    # If validation is successful, proceed to apply changes.
    apply_changes(data_to_validate, output_directory, args.dry_run, args.yes)


if __name__ == "__main__":
    main()
