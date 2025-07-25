# aicodec/review_server.py
import http.server
import socketserver
import webbrowser
import os
import json
import argparse
from pathlib import Path

PORT = 8000


class ReviewHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    output_dir = "."
    original_file_path = None
    changes_file_path = None

    def do_GET(self):
        # Handle API endpoint for fetching initial context
        if self.path == '/api/context':
            print("hello from api/context")
            try:
                with open(self.original_file_path, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
                with open(self.changes_file_path, 'r', encoding='utf-8') as f:
                    changes_data = json.load(f)

                response_data = {
                    'original': original_data,
                    'changes': changes_data
                }

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                # Add CORS header if needed
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                number_of_bytes = self.wfile.write(
                    json.dumps(response_data).encode('utf-8'))
                print(f"sent bytes: {number_of_bytes}")
            except Exception as e:
                print(f"Error in /api/context: {e}")  # Add error logging
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {'status': 'SERVER_ERROR', 'reason': str(e)}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
            return  # IMPORTANT: Return here, don't call super()

        # For all other paths, serve static files
        print(f"Serving static file: {self.path}")
        return super().do_GET()

    def do_POST(self):
        if self.path == '/api/apply':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                changes_to_apply = json.loads(post_data)

                results = self._apply_changes(changes_to_apply)

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(results).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {'status': 'SERVER_ERROR', 'reason': str(e)}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
            return

        self.send_error(404, "File Not Found")

    def _apply_changes(self, changes_list):
        results = []
        for change in changes_list:
            action = change.get('action')
            relative_path = change.get('filePath')
            content = change.get('content', '')
            target_path = Path(self.output_dir) / relative_path

            try:
                if action.upper() in ['CREATE', 'REPLACE']:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(content, encoding='utf-8')
                    results.append({'filePath': relative_path,
                                   'status': 'SUCCESS', 'action': action})
                elif action.upper() == 'DELETE':
                    if target_path.exists():
                        target_path.unlink()
                        results.append(
                            {'filePath': relative_path, 'status': 'SUCCESS', 'action': action})
                    else:
                        results.append(
                            {'filePath': relative_path, 'status': 'SKIPPED', 'reason': 'File not found for DELETE'})
            except Exception as e:
                results.append({'filePath': relative_path,
                               'status': 'FAILURE', 'reason': str(e)})
        return results


def main():
    parser = argparse.ArgumentParser(description="AI Codec Review UI Server")
    parser.add_argument('-od', '--output-dir', type=Path, required=True,
                        help="The project directory to apply changes to.")
    parser.add_argument('--original', type=Path, required=True,
                        help="Path to the original context JSON file.")
    parser.add_argument('--changes', type=Path, required=True,
                        help="Path to the LLM changes JSON file.")
    args = parser.parse_args()

    # Validate that the JSON files exist
    if not args.original.exists():
        print(f"Error: Original file '{args.original}' does not exist.")
        return
    if not args.changes.exists():
        print(f"Error: Changes file '{args.changes}' does not exist.")
        return

    # Set the paths on the handler class
    ReviewHttpRequestHandler.output_dir = str(args.output_dir.resolve())
    ReviewHttpRequestHandler.original_file_path = str(args.original.resolve())
    ReviewHttpRequestHandler.changes_file_path = str(args.changes.resolve())

    review_ui_dir = Path(__file__).parent.parent / 'review-ui'
    if not review_ui_dir.is_dir():
        print(
            f"Error: Could not find the 'review-ui' directory at '{review_ui_dir}'.")
        return

    os.chdir(review_ui_dir)

    Handler = ReviewHttpRequestHandler

    port = PORT
    while True:
        try:
            with socketserver.TCPServer(("", port), Handler) as httpd:
                print(
                    f"Serving at http://localhost:{port} for target directory {args.output_dir.resolve()}")
                print(f"Original file: {args.original.resolve()}")
                print(f"Changes file: {args.changes.resolve()}")
                print("Opening browser... (Press Ctrl+C to stop)")
                webbrowser.open_new_tab(f"http://localhost:{port}")
                httpd.serve_forever()
            break
        except OSError:
            port += 1
        except KeyboardInterrupt:
            print("\nServer stopped.")
            break


if __name__ == '__main__':
    main()
