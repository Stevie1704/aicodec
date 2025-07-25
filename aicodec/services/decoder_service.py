# aicodec/services/decoder_service.py
import os
import json
from jsonschema import validate, ValidationError
from aicodec.core.config import DecoderConfig
from aicodec.core.models import Change, ChangeAction, ChangeSet


class DecoderService:
    def __init__(self, config: DecoderConfig):
        self.config = config

    def run(self, dry_run=False, auto_confirm=False):
        if not self.config.input:
            raise ValueError("Input file must be specified for decoder.")

        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            schema_path = os.path.join(script_dir, '..', 'decoder_schema.json')

            with open(self.config.input, 'r', encoding='utf-8') as f:
                data_to_validate = json.load(f)
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            validate(instance=data_to_validate, schema=schema)
            print("JSON data is valid against the schema.")
        except FileNotFoundError as e:
            print(f"Error: Could not find a required file. {e}")
            return
        except json.JSONDecodeError as e:
            print(
                f"Error: Could not parse input file '{self.config.input}'. Invalid JSON. {e}")
            return
        except ValidationError as e:
            print(
                f"Error: Input file '{self.config.input}' does not conform to the schema. {e.message}")
            return

        changes = [Change(file_path=c['filePath'], action=ChangeAction(
            c['action']), content=c.get('content', '')) for c in data_to_validate['changes']]
        changeset = ChangeSet(
            changes=changes, summary=data_to_validate.get('summary'))

        self._apply_changes(changeset, dry_run, auto_confirm)

    def _apply_changes(self, changeset: ChangeSet, dry_run: bool, auto_confirm: bool):
        print(
            f"Proposed changes will be applied to directory: {self.config.output_dir}\n")
        for change in changeset.changes:
            final_path = os.path.join(self.config.output_dir, change.file_path)
            print(f"- {change.action.value}: {final_path}")

        if dry_run:
            print("\nDry run complete. No files were changed.")
            return

        if not auto_confirm:
            confirm = input("\nDo you want to apply these changes? (y/n): ")
            if confirm.lower() != 'y':
                print("Operation cancelled.")
                return

        print("\nApplying changes...")
        for change in changeset.changes:
            target_path = os.path.join(
                self.config.output_dir, change.file_path)
            if change.action in [ChangeAction.CREATE, ChangeAction.REPLACE]:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(change.content)
                print(f"SUCCESS: {change.action.value}D {target_path}")
            elif change.action == ChangeAction.DELETE:
                if os.path.exists(target_path):
                    os.remove(target_path)
                    print(f"SUCCESS: DELETED {target_path}")
                else:
                    print(f"WARNING: File to delete not found: {target_path}")
