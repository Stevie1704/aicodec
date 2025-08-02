# aicodec/review_server.py
import http.server
import socketserver
import webbrowser
import os
import json
import hashlib
from pathlib import Path
from typing import Literal
import uuid
from datetime import datetime

PORT = 8000


class ReviewHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    output_dir = "."
    changes_file_path = None
    ui_mode: Literal['apply', 'revert'] = 'apply'
    session_id = None  # Track the current UI session

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

    def _load_existing_revert_data(self, revert_file_path: Path) -> dict:
        """Load existing revert data from file, handling both old and new formats."""
        if not revert_file_path.exists():
            return {"changes": [], "session_id": None, "session_start": None}
        
        try:
            with open(revert_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle legacy format (just changes array)
            if isinstance(data.get('changes'), list) and 'session_id' not in data:
                return {
                    "changes": data.get('changes', []),
                    "session_id": None,
                    "session_start": None,
                    "summary": data.get('summary', '')
                }
            
            return data
        except (json.JSONDecodeError, FileNotFoundError):
            return {"changes": [], "session_id": None, "session_start": None}

    def _merge_revert_changes(self, existing_changes: list, new_changes: list) -> list:
        """Merge new revert changes with existing ones, handling conflicts intelligently."""
        # Create a map of existing changes by file path for quick lookup
        existing_map = {}
        for change in existing_changes:
            file_path = change.get('filePath')
            if file_path:
                existing_map[file_path] = change
        
        merged_changes = existing_changes.copy()
        
        for new_change in new_changes:
            file_path = new_change.get('filePath')
            if not file_path:
                continue
            
            if file_path in existing_map:
                # File was already modified in this session
                existing_change = existing_map[file_path]
                
                # The new change represents what we need to do to revert the current operation
                # We need to update the existing revert entry to reflect the original state
                # before any changes in this session
                
                if new_change['action'] == 'DELETE':
                    # Current operation created the file, so we still want to delete it
                    # Keep the existing change as-is since it represents the original state
                    pass
                elif new_change['action'] == 'CREATE':
                    # Current operation deleted the file, but it was modified earlier in session
                    # The revert should restore to the original content from before the session
                    existing_change['action'] = 'CREATE'
                    # Keep the original content from existing_change
                elif new_change['action'] == 'REPLACE':
                    # File was replaced, keep the original content from the first change in session
                    existing_change['action'] = 'REPLACE'
                    # Keep the original content from existing_change
            else:
                # File is being modified for the first time in this session
                merged_changes.append(new_change)
                existing_map[file_path] = new_change
        
        return merged_changes

    def _apply_changes(self, changes_list):
        results = []
        new_revert_changes = []
        output_path_abs = Path(self.output_dir).resolve()
        
        # Load existing revert data
        revert_file_dir = output_path_abs / '.aicodec'
        revert_file_path = revert_file_dir / 'revert.json'
        existing_revert_data = self._load_existing_revert_data(revert_file_path)
        
        # Check if this is a new session or continuation of existing session
        current_session_id = self.session_id
        if (current_session_id != existing_revert_data.get('session_id') or 
            self.ui_mode == 'revert'):
            # New session or revert mode - start fresh
            is_new_session = True
            session_start_time = datetime.now().isoformat()
        else:
            # Continuing existing session
            is_new_session = False
            session_start_time = existing_revert_data.get('session_start')

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
                        new_revert_changes.append({
                            'filePath': relative_path, 
                            'action': revert_action, 
                            'content': revert_content
                        })

                elif action.upper() == 'DELETE':
                    if target_path.exists():
                        if self.ui_mode == 'apply': # We must capture content before deleting
                           original_content = target_path.read_text(encoding='utf-8')
                        target_path.unlink()
                        if self.ui_mode == 'apply':
                            new_revert_changes.append({
                                'filePath': relative_path, 
                                'action': 'CREATE', 
                                'content': original_content
                            })
                    else:
                        results.append(
                            {'filePath': relative_path, 'status': 'SKIPPED', 'reason': 'File not found for DELETE'})
                        continue # Don't add to results or revert log

                results.append({'filePath': relative_path, 'status': 'SUCCESS', 'action': action})

            except Exception as e:
                results.append({'filePath': relative_path,
                               'status': 'FAILURE', 'reason': str(e)})

        # --- Save the revert file if in 'apply' mode and changes were made ---
        if self.ui_mode == 'apply' and new_revert_changes:
            revert_file_dir.mkdir(exist_ok=True)
            
            if is_new_session:
                # Start new session
                merged_revert_changes = new_revert_changes
                session_summary = "Session-based revert data for aicodec apply operations. This file accumulates all changes from a UI session."
            else:
                # Merge with existing session changes
                merged_revert_changes = self._merge_revert_changes(
                    existing_revert_data.get('changes', []), 
                    new_revert_changes
                )
                session_summary = existing_revert_data.get('summary', 
                    "Session-based revert data for aicodec apply operations. This file accumulates all changes from a UI session.")
            
            revert_data = {
                "summary": session_summary,
                "changes": merged_revert_changes,
                "session_id": current_session_id,
                "session_start": session_start_time,
                "last_updated": datetime.now().isoformat(),
                "total_operations": len(merged_revert_changes)
            }
            
            with open(revert_file_path, 'w', encoding='utf-8') as f:
                json.dump(revert_data, f, indent=4)
            
            print(f"Session revert information updated: {len(new_revert_changes)} new change(s), {len(merged_revert_changes)} total in session")
            print(f"Revert data saved to {revert_file_path}")

        return results

def launch_review_server(output_dir: Path, changes_file: Path, mode: Literal['apply', 'revert'] = 'apply'):
    if not changes_file.exists():
        print(f"Error: Changes file '{changes_file}' does not exist.")
        return

    ReviewHttpRequestHandler.output_dir = str(output_dir.resolve())
    ReviewHttpRequestHandler.changes_file_path = str(changes_file.resolve())
    ReviewHttpRequestHandler.ui_mode = mode
    
    # Generate a session ID for this UI session
    if mode == 'apply':
        ReviewHttpRequestHandler.session_id = str(uuid.uuid4())
        print(f"Starting new apply session: {ReviewHttpRequestHandler.session_id}")
    else:
        ReviewHttpRequestHandler.session_id = None
        print("Starting revert session")

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
