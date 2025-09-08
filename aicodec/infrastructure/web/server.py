import http.server
import json
import socketserver
import uuid
import webbrowser
from functools import partial
from pathlib import Path
from typing import Any, Literal

from ...application.services import ReviewService

PORT = 8000


class ReviewHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Stateless HTTP Handler for the review UI."""

    def __init__(self, *args: Any, review_service: ReviewService, session_id: str | None, **kwargs: Any):
        self.review_service = review_service
        self.session_id = session_id
        # The 'directory' kwarg tells SimpleHTTPRequestHandler where to serve files from.
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        if self.path == '/':
            self.path = 'ui/index.html'

        if self.path == '/api/context':
            self._handle_get_context()
            return

        # The base handler will serve files from the directory passed in __init__
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self) -> None:
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length))

            if self.path == '/api/apply':
                results = self.review_service.apply_changes(
                    post_data, self.session_id)
                self._send_json_response(results)
            elif self.path == '/api/save':
                self.review_service.save_editable_changes(post_data)
                self._send_json_response({'status': 'SUCCESS'})
            else:
                self.send_error(404, "Not Found")

        except Exception as e:
            self._send_server_error(e)

    def _handle_get_context(self) -> None:
        try:
            response_data = self.review_service.get_review_context()
            self._send_json_response(response_data)
        except Exception as e:
            self._send_server_error(e)

    def _send_json_response(self, data: Any, status_code: int = 200) -> None:
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        # Prevent caching of API responses
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def _send_server_error(self, e: Exception) -> None:
        self.log_error("Server error: %s", e)
        error_response = {'status': 'SERVER_ERROR', 'reason': str(e)}
        self._send_json_response(error_response, 500)


def launch_review_server(review_service: ReviewService, mode: Literal['apply', 'revert'] = 'apply') -> None:
    session_id = None
    if mode == 'apply':
        session_id = str(uuid.uuid4())
        print(f"Starting new apply session: {session_id}")
    else:
        print("Starting revert session")

    web_dir = Path(__file__).parent
    ui_dir = web_dir / 'ui'
    if not ui_dir.is_dir():
        print(
            f"Error: Could not find the 'ui' directory at '{ui_dir}'. Package might be broken.")
        return

    # Use functools.partial to create a handler instance with our service and session data,
    # making the handler itself stateless and avoiding global state or os.chdir.
    Handler = partial(
        ReviewHttpRequestHandler,
        review_service=review_service,
        session_id=session_id,
        # Serve files relative to the server.py location
        directory=str(web_dir)
    )

    port = PORT
    while True:
        try:
            # Use 'localhost' to ensure the server is only accessible locally
            with socketserver.TCPServer(("localhost", port), Handler) as httpd:
                url = f"http://localhost:{port}"
                print(
                    f"Serving at {url} for target directory {review_service.output_dir.resolve()}")
                print("Press Ctrl+C to stop the server.")
                webbrowser.open_new_tab(url)
                httpd.serve_forever()
            break
        except OSError as e:
            # Address already in use (Linux/macOS/Windows)
            if e.errno in (98, 48, 10048):
                print(f"Port {port} is in use, trying next one...")
                port += 1
            else:
                print(f"An unexpected OS error occurred: {e}")
                break
        except KeyboardInterrupt:
            print("\nServer stopped by user.")
            break
