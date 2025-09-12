# tests/test_infra_web.py
import http.server
import io
import json
from unittest.mock import ANY, MagicMock, patch

import pytest

from aicodec.application.services import ReviewService
from aicodec.infrastructure.web.server import ReviewHttpRequestHandler, launch_review_server


@pytest.fixture
def mock_review_service(tmp_path):
    service = MagicMock(spec=ReviewService)
    service.output_dir = tmp_path
    return service


@pytest.fixture
def handler_factory(mock_review_service):
    def factory(path, post_data=b'{}', headers=None):
        with patch.object(http.server.SimpleHTTPRequestHandler, '__init__', lambda x, *a, **k: None):
            handler = ReviewHttpRequestHandler(
                review_service=mock_review_service,
                session_id='test-session',
                directory=None
            )
        
        handler.path = path
        handler.headers = headers or {'Content-Length': str(len(post_data))}
        handler.rfile = io.BytesIO(post_data)
        handler.wfile = io.BytesIO()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.log_error = MagicMock()
        return handler
    return factory


class TestReviewHttpRequestHandler:

    def test_do_get_root(self, handler_factory):
        handler = handler_factory('/')
        with patch('http.server.SimpleHTTPRequestHandler.do_GET') as mock_super_get:
            handler.do_GET()
        assert handler.path == 'ui/index.html'
        mock_super_get.assert_called_once()

    def test_do_get_context_api(self, handler_factory, mock_review_service):
        context_data = {'summary': 'test'}
        mock_review_service.get_review_context.return_value = context_data
        handler = handler_factory('/api/context')
        
        handler.do_GET()
        
        handler.send_response.assert_called_with(200)
        handler.send_header.assert_any_call('Content-type', 'application/json')
        handler.wfile.seek(0)
        response_body = json.loads(handler.wfile.read())
        assert response_body == context_data

    def test_do_post_apply_api(self, handler_factory, mock_review_service):
        mock_review_service.apply_changes.return_value = []
        post_body = json.dumps([{'filePath': 'a.py'}]).encode('utf-8')
        handler = handler_factory('/api/apply', post_data=post_body)
        
        handler.do_POST()

        mock_review_service.apply_changes.assert_called_once_with([{'filePath': 'a.py'}], 'test-session')
        handler.send_response.assert_called_with(200)
        
    def test_do_post_save_api(self, handler_factory, mock_review_service):
        post_body = json.dumps({'summary': 's'}).encode('utf-8')
        handler = handler_factory('/api/save', post_data=post_body)
        
        handler.do_POST()
        
        mock_review_service.save_editable_changes.assert_called_once_with({'summary': 's'})
        handler.send_response.assert_called_with(200)

    def test_api_server_error(self, handler_factory, mock_review_service):
        mock_review_service.get_review_context.side_effect = Exception("Test DB error")
        handler = handler_factory('/api/context')

        handler._handle_get_context()

        handler.send_response.assert_called_with(500)
        handler.wfile.seek(0)
        response_body = json.loads(handler.wfile.read())
        assert response_body['status'] == 'SERVER_ERROR'
        assert 'Test DB error' in response_body['reason']


@patch('aicodec.infrastructure.web.server.socketserver.TCPServer')
@patch('aicodec.infrastructure.web.server.webbrowser.open_new_tab')
def test_launch_server(mock_webbrowser, mock_server, mock_review_service, tmp_path):
    ui_dir = tmp_path / 'aicodec' / 'infrastructure' / 'web' / 'ui'
    ui_dir.mkdir(parents=True)
    with patch('pathlib.Path.is_dir', return_value=True):
        mock_server.return_value.__enter__.return_value.serve_forever.side_effect = KeyboardInterrupt()
        launch_review_server(mock_review_service, mode='apply')
        
    mock_server.assert_called_with(('localhost', 8000), ANY)
    mock_webbrowser.assert_called_once()


@patch('aicodec.infrastructure.web.server.socketserver.TCPServer')
@patch('aicodec.infrastructure.web.server.webbrowser.open_new_tab')
def test_launch_server_port_conflict(mock_webbrowser, mock_server, mock_review_service, tmp_path):
    mock_server.side_effect = [
        OSError(98, 'Address already in use'),
        MagicMock()
    ]
    ui_dir = tmp_path / 'aicodec' / 'infrastructure' / 'web' / 'ui'
    ui_dir.mkdir(parents=True)
    with patch('pathlib.Path.is_dir', return_value=True):
        mock_server.return_value.__enter__.return_value.serve_forever.side_effect = KeyboardInterrupt()
        launch_review_server(mock_review_service, mode='revert')

    assert mock_server.call_count == 2
    assert mock_server.call_args_list[0].args[0] == ('localhost', 8000)
    assert mock_server.call_args_list[1].args[0] == ('localhost', 8001)
