# aicodec/review_server.py
import http.server
import socketserver
import webbrowser
import os
import json
import hashlib
from pathlib import Path
from typing import Literal

PORT = 8000


class ReviewHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    output_dir = "."
    changes_file_path = None
    ui_mode: Literal['apply', 'revert'] = 'apply'

    def do_GET(self):
        if self.path == '/':
            self.path = 'index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

        if self.path == '/api/context':
            try:
                with open(self.changes_file_path, 'r', encoding='utf-8') as f:
                    changes_data = json.load(f)

                processed_changes = []
                source_summary = changes_data.get("summary", "No summary provided.")
                source_changes = changes_data.get("changes", [])

                for change in source_changes:
                    relative_path = change.get('filePath')
                    if not relative_path:
                        continue

                    # This is the content from the source file (changes.json or revert.json)
                    proposed_content = change.get('content', '')
                    # This is the action from the source file.
                    action = change.get('action', '').upper()
                    target_path = Path(self.output_dir).resolve().joinpath(relative_path)

                    original_content = ""
                    should_include = False

                    if target_path.exists():
                        try:
                            original_content = target_path.read_text(encoding='utf-8')
                        except Exception:
                            original_content = "<Cannot read binary file>"
                        
                        # If the action from the file is CREATE, but the file exists on disk,
                        # it's effectively a REPLACE from the user's perspective.
                        if action == 'CREATE':
                            action = 'REPLACE'

                        # For REPLACE actions, only include them if content is different.
                        if action == 'REPLACE':
                            hash_on_disk = hashlib.sha256(original_content.encode('utf-8')).hexdigest()
                            hash_proposed = hashlib.sha256(proposed_content.encode('utf-8')).hexdigest()
                            if hash_on_disk != hash_proposed:
                                should_include = True
                        # Deletions are always included.
                        elif action == 'DELETE':
                            proposed_content = "" # For a deletion, the right side of the diff is empty
                            should_include = True

                    else: # File does not exist on disk
                        # If the action is to delete a non-existent file, skip it.
                        if action == 'DELETE':
                            continue
                        # Otherwise, it's a CREATE action.
                        if action in ['CREATE', 'REPLACE']:
                            action = 'CREATE'
                            should_include = True

                    if should_include:
                        processed_changes.append({
                            "filePath": relative_path,
                            "original_content": original_content, # Content on disk (left side of diff)
                            "proposed_content": proposed_content, # Content from file (right side of diff)
                            "action": action
                        })

                response_data = {
                    'summary': source_summary,
                    'changes': processed_changes,
                    'mode': self.ui_mode
                }

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {'status': 'SERVER_ERROR', 'reason': str(e)}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
            return

        return super().do_GET()

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data_raw = self.rfile.read(content_length)
            post_data = json.loads(post_data_raw)

            if self.path == '/api/apply':
                results = self._apply_changes(post_data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(results).encode('utf-8'))

            elif self.path == '/api/save':
                self._save_changes_to_file(post_data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'SUCCESS'}).encode('utf-8'))

            else:
                self.send_error(404, "File Not Found")

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {'status': 'SERVER_ERROR', 'reason': str(e)}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))

    def _save_changes_to_file(self, data):
        """Saves the entire changes object back to the changes.json file."""
        with open(self.changes_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def _apply_changes(self, changes_list):
        results = []
        revert_changes = []
        output_path_abs = Path(self.output_dir).resolve()

        for change in changes_list:
            action = change.get('action')
            relative_path = change.get('filePath')
            content = change.get('content', '')
            target_path = output_path_abs.joinpath(relative_path).resolve()

            if output_path_abs not in target_path.parents and target_path != output_path_abs:
                results.append({'filePath': relative_path, 'status': 'FAILURE',
                               'reason': 'Directory traversal attempt blocked.'})
                continue

            try:
                # --- Capture original state for revert log (only in apply mode) ---
                if self.ui_mode == 'apply':
                    original_content = ""
                    file_existed = target_path.exists()
                    if file_existed:
                        try:
                            original_content = target_path.read_text(encoding='utf-8')
                        except Exception:
                            pass  # Ignore read errors for binary files

                # --- Apply the change ---
                if action.upper() in ['CREATE', 'REPLACE']:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(content, encoding='utf-8')
                    if self.ui_mode == 'apply':
                        revert_action = 'REPLACE' if file_existed else 'DELETE'
                        revert_content = original_content if file_existed else ''
                        revert_changes.append({'filePath': relative_path, 'action': revert_action, 'content': revert_content})

                elif action.upper() == 'DELETE':
                    if target_path.exists():
                        if self.ui_mode == 'apply': # We must capture content before deleting
                           original_content = target_path.read_text(encoding='utf-8')
                        target_path.unlink()
                        if self.ui_mode == 'apply':
                            revert_changes.append({'filePath': relative_path, 'action': 'CREATE', 'content': original_content})
                    else:
                        results.append(
                            {'filePath': relative_path, 'status': 'SKIPPED', 'reason': 'File not found for DELETE'})
                        continue # Don't add to results or revert log

                results.append({'filePath': relative_path, 'status': 'SUCCESS', 'action': action})

            except Exception as e:
                results.append({'filePath': relative_path,
                               'status': 'FAILURE', 'reason': str(e)})

        # --- Save the revert file if in 'apply' mode and changes were made ---
        if self.ui_mode == 'apply' and revert_changes:
            revert_file_dir = output_path_abs / '.aicodec'
            revert_file_dir.mkdir(exist_ok=True)
            revert_file_path = revert_file_dir / 'revert.json'
            revert_data = {
                "summary": "Revert data for the last 'aicodec apply' operation. This file is used by 'aicodec revert'.",
                "changes": revert_changes
            }
            with open(revert_file_path, 'w', encoding='utf-8') as f:
                json.dump(revert_data, f, indent=4)
            print(f"Revert information for {len(revert_changes)} change(s) saved to {revert_file_path}")

        return results

def launch_review_server(output_dir: Path, changes_file: Path, mode: Literal['apply', 'revert'] = 'apply'):
    if not changes_file.exists():
        print(f"Error: Changes file '{changes_file}' does not exist.")
        return

    ReviewHttpRequestHandler.output_dir = str(output_dir.resolve())
    ReviewHttpRequestHandler.changes_file_path = str(changes_file.resolve())
    ReviewHttpRequestHandler.ui_mode = mode

    review_ui_dir = Path(__file__).parent.parent / 'review-ui'
    if not review_ui_dir.is_dir():
        print(f"Error: Could not find the 'review-ui' directory at '{review_ui_dir}'.")
        return

    os.chdir(review_ui_dir)

    Handler = ReviewHttpRequestHandler

    port = PORT
    while True:
        try:
            with socketserver.TCPServer(("", port), Handler) as httpd:
                print(
                    f"Serving at http://localhost:{port} for target directory {output_dir.resolve()}")
                webbrowser.open_new_tab(f"http://localhost:{port}")
                httpd.serve_forever()
            break
        except OSError:
            port += 1
        except KeyboardInterrupt:
            print("\nServer stopped.")
            break
