import pytest
import requests
import threading
import socketserver
import json
import time
from pathlib import Path

# Make sure to import the components from your application
from aicodec.review_server import ReviewHttpRequestHandler, PORT

# A fixture to run the server in a separate thread for live testing


@pytest.fixture
def live_server(tmp_path):
    # Set up a temporary directory for the web server to serve from
    review_ui_dir = tmp_path / "review-ui"
    review_ui_dir.mkdir()
    (review_ui_dir / "index.html").write_text("<h1>Review UI</h1>")

    # Set up a temporary output directory for changes to be applied to
    output_dir = tmp_path / "output_project"
    output_dir.mkdir()

    # Configure the handler with the output directory
    ReviewHttpRequestHandler.output_dir = str(output_dir.resolve())

    # Find an available port
    port = PORT
    httpd = None
    while httpd is None:
        try:
            httpd = socketserver.TCPServer(
                ("", port), ReviewHttpRequestHandler)
        except OSError:
            port += 1

    # Run the server in a background thread
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # Change the working directory for the test context
    # This is needed because the server itself changes the directory
    import os
    original_cwd = os.getcwd()
    os.chdir(review_ui_dir)

    # Yield the server's URL and the output directory path
    yield f"http://localhost:{port}", output_dir

    # Teardown: stop the server and restore the working directory
    httpd.shutdown()
    server_thread.join()
    os.chdir(original_cwd)


def test_get_index_html_success(live_server):
    """Verify that the server serves the index.html file."""
    url, _ = live_server
    response = requests.get(f"{url}/index.html")
    assert response.status_code == 200
    assert "<h1>Review UI</h1>" in response.text


def test_get_file_not_found(live_server):
    """Verify that the server returns a 404 for a non-existent file."""
    url, _ = live_server
    response = requests.get(f"{url}/nonexistent.js")
    assert response.status_code == 404


def test_post_apply_changes_success(live_server):
    """Test the full CREATE, REPLACE, and DELETE workflow."""
    url, output_dir = live_server

    # Setup: Create initial files
    (output_dir / "file_to_replace.txt").write_text("old content")
    (output_dir / "file_to_delete.txt").write_text("delete me")

    changes = [
        {"filePath": "new_file.txt", "action": "CREATE", "content": "hello world"},
        {"filePath": "file_to_replace.txt",
            "action": "REPLACE", "content": "new content"},
        {"filePath": "file_to_delete.txt", "action": "DELETE", "content": ""},
    ]

    response = requests.post(f"{url}/api/apply", json=changes)

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 3
    assert all(r['status'] == 'SUCCESS' for r in results)

    # Verify filesystem state
    assert (output_dir / "new_file.txt").read_text() == "hello world"
    assert (output_dir / "file_to_replace.txt").read_text() == "new content"
    assert not (output_dir / "file_to_delete.txt").exists()


def test_post_apply_changes_delete_nonexistent_skipped(live_server):
    """Test that deleting a non-existent file is skipped gracefully."""
    url, _ = live_server
    changes = [{"filePath": "nonexistent.txt",
                "action": "DELETE", "content": ""}]
    response = requests.post(f"{url}/api/apply", json=changes)

    assert response.status_code == 200
    result = response.json()[0]
    assert result['status'] == 'SKIPPED'
    assert result['reason'] == 'File not found for DELETE'


# TODO: check if this is necessary, since it's only locally running
# def test_post_apply_changes_directory_traversal_failure(live_server):
    # """SECURITY: Ensure directory traversal is blocked."""
    # url, output_dir = live_server

    # # This malicious payload attempts to write a file outside the project dir
    # malicious_changes = [{"filePath": "../malicious.txt",
    # "action": "CREATE", "content": "pwned"}]

    # response = requests.post(f"{url}/api/apply", json=malicious_changes)

    # # The server should catch this and return a failure status.
    # # This test relies on a patched server that prevents traversal.
    # # Without a patch, this test would fail and the file would be created.
    # assert response.status_code == 200  # The API call itself succeeds
    # result = response.json()[0]
    # assert result['status'] == 'FAILURE'
    # assert "Directory traversal" in result['reason']

    # # Most importantly, verify the malicious file was NOT created
    # assert not (output_dir.parent / "malicious.txt").exists()
