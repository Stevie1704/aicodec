import pytest
import requests
import threading
import socketserver
import json
import time
import os
from pathlib import Path
from unittest.mock import MagicMock

from aicodec.review_server import ReviewHttpRequestHandler, PORT, launch_review_server

@pytest.fixture
def temp_files(tmp_path):
    # Dir for the review UI static files
    review_ui_dir = tmp_path / "review-ui"
    review_ui_dir.mkdir()
    (review_ui_dir / "index.html").write_text("<h1>Review UI</h1>")

    # Dir where changes will be applied
    output_dir = tmp_path / "output_project"
    output_dir.mkdir()

    # Dummy data files
    original_context_file = tmp_path / "context.json"
    original_context_file.write_text(json.dumps([{"filePath": "file.txt", "content": "original"}]))

    changes_file = tmp_path / "changes.json"
    changes_file.write_text(json.dumps({"summary": "test", "changes": []}))

    return {
        "review_ui_dir": review_ui_dir,
        "output_dir": output_dir,
        "original_context_file": original_context_file,
        "changes_file": changes_file
    }

@pytest.fixture
def live_server(temp_files):
    # Configure the handler with paths from the temp_files fixture
    ReviewHttpRequestHandler.output_dir = str(temp_files["output_dir"].resolve())
    ReviewHttpRequestHandler.original_file_path = str(temp_files["original_context_file"].resolve())
    ReviewHttpRequestHandler.changes_file_path = str(temp_files["changes_file"].resolve())

    # Find an available port
    port = PORT
    httpd = None
    while httpd is None:
        try:
            httpd = socketserver.TCPServer(("", port), ReviewHttpRequestHandler)
        except OSError:
            port += 1

    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    original_cwd = os.getcwd()
    os.chdir(temp_files["review_ui_dir"])

    yield f"http://localhost:{port}", temp_files["output_dir"]

    httpd.shutdown()
    httpd.server_close()
    server_thread.join()
    os.chdir(original_cwd)


# --- Test HTTP Endpoints ---

def test_get_index_html_success(live_server):
    url, _ = live_server
    response = requests.get(f"{url}/index.html")
    assert response.status_code == 200
    assert "<h1>Review UI</h1>" in response.text

def test_get_file_not_found(live_server):
    url, _ = live_server
    response = requests.get(f"{url}/nonexistent.js")
    assert response.status_code == 404

def test_get_api_context_success(live_server):
    url, _ = live_server
    response = requests.get(f"{url}/api/context")
    assert response.status_code == 200
    data = response.json()
    assert 'original' in data
    assert 'changes' in data
    assert data['original'][0]['filePath'] == 'file.txt'

def test_get_api_context_server_error(live_server, temp_files):
    url, _ = live_server
    # Make a file unreadable to trigger an error
    temp_files["original_context_file"].unlink()
    response = requests.get(f"{url}/api/context")
    assert response.status_code == 500
    data = response.json()
    assert data['status'] == 'SERVER_ERROR'

def test_post_apply_changes_success(live_server):
    url, output_dir = live_server
    (output_dir / "file_to_replace.txt").write_text("old content")
    (output_dir / "file_to_delete.txt").write_text("delete me")

    changes = [
        {"filePath": "new_file.txt", "action": "CREATE", "content": "hello world"},
        {"filePath": "file_to_replace.txt", "action": "REPLACE", "content": "new content"},
        {"filePath": "file_to_delete.txt", "action": "DELETE", "content": ""},
    ]

    response = requests.post(f"{url}/api/apply", json=changes)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 3
    assert all(r['status'] == 'SUCCESS' for r in results)
    assert (output_dir / "new_file.txt").read_text() == "hello world"
    assert (output_dir / "file_to_replace.txt").read_text() == "new content"
    assert not (output_dir / "file_to_delete.txt").exists()

def test_post_apply_changes_delete_nonexistent_skipped(live_server):
    url, _ = live_server
    changes = [{"filePath": "nonexistent.txt", "action": "DELETE", "content": ""}]
    response = requests.post(f"{url}/api/apply", json=changes)
    assert response.status_code == 200
    result = response.json()[0]
    assert result['status'] == 'SKIPPED'

def test_post_apply_changes_directory_traversal_failure(live_server):
    url, output_dir = live_server
    malicious_changes = [{"filePath": "../malicious.txt", "action": "CREATE", "content": "pwned"}]
    response = requests.post(f"{url}/api/apply", json=malicious_changes)
    assert response.status_code == 200
    result = response.json()[0]
    assert result['status'] == 'FAILURE'
    assert "Directory traversal" in result['reason']
    assert not (output_dir.parent / "malicious.txt").exists()

def test_post_apply_malformed_json_fails(live_server):
    url, _ = live_server
    headers = {'Content-Type': 'application/json'}
    response = requests.post(f"{url}/api/apply", data='{not_json}', headers=headers)
    assert response.status_code == 500
    assert response.json()['status'] == 'SERVER_ERROR'

def test_post_apply_filesystem_permission_error(live_server, mocker):
    url, _ = live_server
    mocker.patch.object(Path, 'write_text', side_effect=PermissionError("Access denied"))
    changes = [{"filePath": "new_file.txt", "action": "CREATE", "content": "hello world"}]
    response = requests.post(f"{url}/api/apply", json=changes)
    assert response.status_code == 200
    result = response.json()[0]
    assert result['status'] == 'FAILURE'
    assert 'Access denied' in result['reason']

# --- Test Server Launch Logic ---

def test_launch_server_file_not_found(capsys, temp_files):
    non_existent_file = temp_files["output_dir"] / "nonexistent.json"
    launch_review_server(temp_files["output_dir"], non_existent_file, temp_files["changes_file"])
    captured = capsys.readouterr()
    assert f"Error: Original file '{non_existent_file.resolve()}' does not exist." in captured.out

def test_launch_server_ui_dir_not_found(capsys, temp_files, mocker):
    mocker.patch('pathlib.Path.is_dir', return_value=False)
    launch_review_server(temp_files["output_dir"], temp_files["original_context_file"], temp_files["changes_file"])
    captured = capsys.readouterr()
    assert "Error: Could not find the 'review-ui' directory" in captured.out

def test_launch_server_port_in_use(capsys, temp_files, mocker):
    # Mock the server to simulate port conflict on the first try
    mock_server = MagicMock()
    mock_server.side_effect = [OSError, MagicMock()]
    mocker.patch('socketserver.TCPServer', new=mock_server)

    # Mock functions that would block the test
    mocker.patch('webbrowser.open_new_tab')
    mocker.patch('socketserver.TCPServer.__enter__') # Prevent serve_forever
    mocker.patch('socketserver.TCPServer.__exit__')

    launch_review_server(temp_files["output_dir"], temp_files["original_context_file"], temp_files["changes_file"])
    captured = capsys.readouterr()
    # Check that the server eventually started on the next port
    assert f"Serving at http://localhost:{PORT + 1}" in captured.out
    assert mock_server.call_count == 2
