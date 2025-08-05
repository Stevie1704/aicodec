# aicodec/infrastructure/web/server.py
import http.server
import socketserver
import webbrowser
import os
import json
import uuid
from pathlib import Path
from typing import Literal

from ...application.services import ReviewService

PORT = 8000


class ReviewHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    review_service: ReviewService = None
    session_id: str = None

    def do_GET(self):
        if self.path == '/':
            self.path = 'ui/index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

        if self.path == '/api/context':
            try:
                response_data = self.review_service.get_review_context()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            except Exception as e:
                self._send_server_error(e)
            return

        # Serve UI assets from the 'ui' subdirectory
        if self.path.startswith('/ui/'):
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

        return super().do_GET()

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length))

            if self.path == '/api/apply':
                results = self.review_service.apply_changes(post_data, self.session_id)
                self._send_json_response(results)

            elif self.path == '/api/save':
                self.review_service.save_editable_changes(post_data)
                self._send_json_response({'status': 'SUCCESS'})

            else:
                self.send_error(404, "Not Found")

        except Exception as e:
            self._send_server_error(e)

    def _send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def _send_server_error(self, e):
        error_response = {'status': 'SERVER_ERROR', 'reason': str(e)}
        self._send_json_response(error_response, 500)


def launch_review_server(review_service: ReviewService, mode: Literal['apply', 'revert'] = 'apply'):
    ReviewHttpRequestHandler.review_service = review_service
    if mode == 'apply':
        ReviewHttpRequestHandler.session_id = str(uuid.uuid4())
        print(f"Starting new apply session: {ReviewHttpRequestHandler.session_id}")
    else:
        ReviewHttpRequestHandler.session_id = None
        print("Starting revert session")

    web_dir = Path(__file__).parent
    ui_dir = web_dir / 'ui'
    if not ui_dir.is_dir():
        print(f"Error: Could not find the 'ui' directory at '{ui_dir}'.")
        return

    os.chdir(web_dir)

    port = PORT
    while True:
        try:
            with socketserver.TCPServer(("", port), ReviewHttpRequestHandler) as httpd:
                url = f"http://localhost:{port}"
                print(f"Serving at {url} for target directory {review_service.output_dir.resolve()}")
                webbrowser.open_new_tab(url)
                httpd.serve_forever()
            break
        except OSError as e:
            if e.errno == 98: # Address already in use
                port += 1
            else:
                raise
        except KeyboardInterrupt:
            print("\nServer stopped.")
            break
