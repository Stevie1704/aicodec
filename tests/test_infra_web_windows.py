from unittest.mock import MagicMock, patch

from aicodec.application.services import ReviewService
from aicodec.infrastructure.web.server import launch_review_server


@patch('aicodec.infrastructure.web.server.socketserver.TCPServer')
@patch('aicodec.infrastructure.web.server.webbrowser.open_new_tab')
def test_launch_server_windows_port_conflict(mock_webbrowser, mock_server, tmp_path):
    service = MagicMock(spec=ReviewService)
    service.output_dir = tmp_path

    # Simulate Linux/macOS errno and then Windows errno before success
    mock_server.side_effect = [
        OSError(98, 'Address already in use'),
        OSError(10048, 'Only one usage of each socket address (protocol/network address/port) is normally permitted'),
        MagicMock()
    ]

    ui_dir = tmp_path / 'aicodec' / 'infrastructure' / 'web' / 'ui'
    ui_dir.mkdir(parents=True)

    with patch('pathlib.Path.is_dir', return_value=True):
        mock_server.return_value.__enter__.return_value.serve_forever.side_effect = KeyboardInterrupt()
        launch_review_server(service, mode='revert')

    assert mock_server.call_count == 3
    assert mock_server.call_args_list[0].args[0] == ('localhost', 8000)
    assert mock_server.call_args_list[1].args[0] == ('localhost', 8001)
    assert mock_server.call_args_list[2].args[0] == ('localhost', 8002)
