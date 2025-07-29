import pytest
import requests
import threading
import socketserver
import json
import os
from pathlib import Path
from unittest.mock import MagicMock

from aicodec.review_server import ReviewHttpRequestHandler, PORT, launch_review_server

@pytest.fixture
def temp_files(tmp_path):
    review_ui_dir = tmp_path / "review-ui"
    review_ui_dir.mkdir()
    (review_ui_dir / "index.html").write_text("<h1>Review UI</h1>")

    output_dir = tmp_path / "output_project"
    output_dir.mkdir()
    # Create a pre-existing file to test REPLACE and DELETE cases
    (output_dir / "existing.txt").write_text("original content")

    # Dummy changes file from the LLM
    changes_file = tmp_path / "changes.json"
    llm_changes = {
        "summary": "Test summary",
        "changes": [
            # This should become CREATE
            {"filePath": "new_file.txt", "action": "CREATE", "content": "new content"},
            # This should become REPLACE
            {"filePath": "existing.txt", "action": "CREATE", "content": "replaced content"},
            # This should remain DELETE
            {"filePath": "existing.txt", "action": "DELETE", "content": ""},
            # This should be skipped
            {"filePath": "non_existent_for_delete.txt", "action": "DELETE", "content": ""}
        ]
    }
    changes_file.write_text(json.dumps(llm_changes))

    return {
        "review_ui_dir": review_ui_dir,
        "output_dir": output_dir,
        "changes_file": changes_file
    }

@pytest.fixture
def live_server(temp_files):
    ReviewHttpRequestHandler.output_dir = str(temp_files["output_dir"].resolve())
    ReviewHttpRequestHandler.changes_file_path = str(temp_files["changes_file"].resolve())

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

def test_get_api_context_live_filesystem(live_server):
    """Test that the API correctly reflects the live filesystem state."""
    url, _ = live_server
    response = requests.get(f"{url}/api/context")
    assert response.status_code == 200
    data = response.json()
    
    assert data['summary'] == "Test summary"
    changes = data['changes']
    
    # There should be 3 changes, as one DELETE was for a non-existent file and was skipped
    assert len(changes) == 3

    # Find each change and verify its corrected state
    create_change = next(c for c in changes if c['filePath'] == 'new_file.txt')
    replace_change = next(c for c in changes if c['filePath'] == 'existing.txt' and c['action'] == 'REPLACE')
    delete_change = next(c for c in changes if c['filePath'] == 'existing.txt' and c['action'] == 'DELETE')

    # Verify CREATE action
    assert create_change['action'] == 'CREATE'
    assert create_change['original_content'] == ''
    assert create_change['proposed_content'] == 'new content'

    # Verify REPLACE action
    assert replace_change['action'] == 'REPLACE'
    assert replace_change['original_content'] == 'original content'
    assert replace_change['proposed_content'] == 'replaced content'

    # Verify DELETE action
    assert delete_change['action'] == 'DELETE'
    assert delete_change['original_content'] == 'original content'
    assert delete_change['proposed_content'] == ''

def test_get_api_context_server_error(live_server, temp_files):
    url, _ = live_server
    # Make a file unreadable to trigger an error
    temp_files["changes_file"].unlink()
    response = requests.get(f"{url}/api/context")
    assert response.status_code == 500
    data = response.json()
    assert data['status'] == 'SERVER_ERROR'

# --- Test Server Launch Logic ---

def test_launch_server_file_not_found(capsys, temp_files):
    non_existent_file = temp_files["output_dir"] / "nonexistent.json"
    launch_review_server(temp_files["output_dir"], non_existent_file)
    captured = capsys.readouterr()
    assert f"Error: Changes file '{non_existent_file.resolve()}' does not exist." in captured.out
