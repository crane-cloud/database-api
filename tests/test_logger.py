import unittest
from unittest.mock import MagicMock
from datetime import datetime
from config import settings
from app.helpers.logger import send_log_message, log_response, send_async_log_message, DEFAULT_DATA

class TestLoggingFunctions(unittest.TestCase):
    def setUp(self):
        self.mock_response = MagicMock(status_code=200)

    def test_send_log_message(self):
        data = {"additional_info": "test"}
        with unittest.mock.patch('app.helpers.logger.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            send_log_message(data)
            mock_post.assert_called_once_with(
                f'{settings.ACTIVITY_LOGGER_URL}/api/activities',
                headers={"Content-Type": "application/json"},
                json={**DEFAULT_DATA, **data}
            )

    def test_log_response(self):
        @log_response
        def test_function():
            return self.mock_response

        with unittest.mock.patch('app.helpers.logger.send_log_message') as mock_send_log_message:
            mock_send_log_message.return_value = None
            response = test_function()
            mock_send_log_message.assert_called_once_with(
                {"route": 'test_function', "status_code": 200}
            )
            self.assertEqual(response, self.mock_response)

    def test_send_async_log_message(self):
        data = {"additional_info": "test"}
        with unittest.mock.patch('app.helpers.logger.Thread') as mock_thread:
            mock_start = MagicMock()
            mock_thread.return_value.start = mock_start
            send_async_log_message(data)
            mock_start.assert_called_once_with()


    def test_send_log_message_exception(self):
        with unittest.mock.patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Test exception")
            
            with unittest.mock.patch('builtins.print') as mock_print:
                send_log_message({})
                mock_print.assert_called_once_with("Error occurred while sending log message: Test exception")

