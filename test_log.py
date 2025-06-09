import unittest
import tempfile
import os
import json
import logging
import io
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime
import collections

# Import the functions we want to test
from log import (
    parse_log_file,
    analyze_by_hour,
    setup_logging,
    load_saved_cookies,
    DiscordHandler,
    send_instance_notification
)


class TestParseLogFile(unittest.TestCase):
    """Test the parse_log_file function"""
    
    def test_parse_log_file_valid_data(self):
        """Test parsing a log file with valid data"""
        log_content = """2024-01-01 10:00:00 [INFO] [GROUP] グループのオンラインメンバー数:5
2024-01-01 11:00:00 [INFO] [GROUP] グループのオンラインメンバー数:8
2024-01-01 12:00:00 [INFO] Some other log entry
2024-01-01 13:00:00 [INFO] [GROUP] グループのオンラインメンバー数:3"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write(log_content)
            temp_path = f.name
        
        try:
            timestamps, user_counts = parse_log_file(temp_path)
            
            self.assertEqual(len(timestamps), 3)
            self.assertEqual(len(user_counts), 3)
            self.assertEqual(user_counts, [5, 8, 3])
            
            # Check timestamps
            expected_times = [
                datetime(2024, 1, 1, 10, 0, 0),
                datetime(2024, 1, 1, 11, 0, 0),
                datetime(2024, 1, 1, 13, 0, 0)
            ]
            self.assertEqual(timestamps, expected_times)
        finally:
            os.unlink(temp_path)
    
    def test_parse_log_file_empty_file(self):
        """Test parsing an empty log file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            timestamps, user_counts = parse_log_file(temp_path)
            self.assertEqual(timestamps, [])
            self.assertEqual(user_counts, [])
        finally:
            os.unlink(temp_path)
    
    def test_parse_log_file_nonexistent(self):
        """Test parsing a non-existent log file"""
        timestamps, user_counts = parse_log_file('nonexistent_file.log')
        self.assertEqual(timestamps, [])
        self.assertEqual(user_counts, [])
    
    def test_parse_log_file_no_matching_lines(self):
        """Test parsing a log file with no matching lines"""
        log_content = """2024-01-01 10:00:00 [INFO] Some random log entry
2024-01-01 11:00:00 [ERROR] Another log entry"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write(log_content)
            temp_path = f.name
        
        try:
            timestamps, user_counts = parse_log_file(temp_path)
            self.assertEqual(timestamps, [])
            self.assertEqual(user_counts, [])
        finally:
            os.unlink(temp_path)


class TestAnalyzeByHour(unittest.TestCase):
    """Test the analyze_by_hour function"""
    
    def test_analyze_by_hour_basic(self):
        """Test basic hour analysis functionality"""
        timestamps = [
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 10, 30, 0),
            datetime(2024, 1, 1, 11, 0, 0),
            datetime(2024, 1, 1, 11, 15, 0),
            datetime(2024, 1, 1, 11, 45, 0)
        ]
        counts = [5, 7, 8, 6, 9]
        
        result = analyze_by_hour(timestamps, counts)
        
        # Should return a defaultdict with hour as key and list of counts as value
        self.assertIsInstance(result, collections.defaultdict)
        self.assertEqual(len(result[10]), 2)  # Two entries for hour 10
        self.assertEqual(len(result[11]), 3)  # Three entries for hour 11
        self.assertEqual(result[10], [5, 7])
        self.assertEqual(result[11], [8, 6, 9])
    
    def test_analyze_by_hour_empty_data(self):
        """Test hour analysis with empty data"""
        result = analyze_by_hour([], [])
        self.assertIsInstance(result, collections.defaultdict)
        self.assertEqual(len(result), 0)
    
    def test_analyze_by_hour_single_entry(self):
        """Test hour analysis with single entry"""
        timestamps = [datetime(2024, 1, 1, 15, 30, 0)]
        counts = [10]
        
        result = analyze_by_hour(timestamps, counts)
        self.assertEqual(len(result[15]), 1)
        self.assertEqual(result[15], [10])


class TestLoadSavedCookies(unittest.TestCase):
    """Test the load_saved_cookies function"""
    
    def test_load_saved_cookies_valid_file(self):
        """Test loading valid cookies from file"""
        cookie_data = {
            "auth": "test_auth_token",
            "twoFactorAuth": "test_2fa_token"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(cookie_data, f)
            temp_path = f.name
        
        try:
            # Mock os.path.exists to return True for our temp file
            with patch('log.os.path.exists') as mock_exists:
                mock_exists.return_value = True
                with patch('builtins.open', mock_open(read_data=json.dumps(cookie_data))):
                    result = load_saved_cookies()
                    self.assertEqual(result, cookie_data)
        finally:
            os.unlink(temp_path)
    
    def test_load_saved_cookies_no_file(self):
        """Test loading cookies when file doesn't exist"""
        with patch('log.os.path.exists') as mock_exists:
            mock_exists.return_value = False
            result = load_saved_cookies()
            self.assertIsNone(result)
    
    def test_load_saved_cookies_invalid_json(self):
        """Test loading cookies with invalid JSON"""
        with patch('log.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('builtins.open', mock_open(read_data='invalid json')):
                result = load_saved_cookies()
                self.assertIsNone(result)


class TestSetupLogging(unittest.TestCase):
    """Test the setup_logging function"""
    
    def setUp(self):
        """Clear any existing handlers before each test"""
        logging.getLogger().handlers.clear()
    
    def tearDown(self):
        """Clean up after each test"""
        logging.getLogger().handlers.clear()
    
    def test_setup_logging_basic(self):
        """Test basic logging setup"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_log_file = f.name
        
        try:
            logger = setup_logging(log_file=temp_log_file)
            
            self.assertIsInstance(logger, logging.Logger)
            self.assertEqual(logger.level, logging.DEBUG)
            
            # Should have at least one handler (file handler)
            self.assertGreaterEqual(len(logger.handlers), 1)
            
            # Test that we can log to it
            logger.info("Test message")
            
            # Check that the log file was created
            self.assertTrue(os.path.exists(temp_log_file))
        finally:
            if os.path.exists(temp_log_file):
                os.unlink(temp_log_file)
    
    def test_setup_logging_with_discord(self):
        """Test logging setup with Discord webhook"""
        webhook_urls = {'LOG': 'https://discord.com/api/webhooks/test'}
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_log_file = f.name
        
        try:
            logger = setup_logging(
                log_file=temp_log_file,
                discord_webhook_urls=webhook_urls
            )
            
            # Should have both file handler and Discord handler
            self.assertEqual(len(logger.handlers), 2)
            
            # Check that one of the handlers is a DiscordHandler
            discord_handlers = [h for h in logger.handlers if isinstance(h, DiscordHandler)]
            self.assertEqual(len(discord_handlers), 1)
        finally:
            if os.path.exists(temp_log_file):
                os.unlink(temp_log_file)


class TestDiscordHandler(unittest.TestCase):
    """Test the DiscordHandler class"""
    
    def test_discord_handler_init(self):
        """Test DiscordHandler initialization"""
        webhook_urls = {'LOG': 'https://discord.com/api/webhooks/test'}
        handler = DiscordHandler(webhook_urls, level=logging.WARNING)
        
        self.assertEqual(handler.webhook_urls, webhook_urls)
        self.assertEqual(handler.level, logging.WARNING)
    
    @patch('log.requests.post')
    def test_discord_handler_emit_warning(self, mock_post):
        """Test DiscordHandler emit method with WARNING level"""
        webhook_urls = {'LOG': 'https://discord.com/api/webhooks/test'}
        handler = DiscordHandler(webhook_urls, level=logging.WARNING)
        
        # Create a log record
        record = logging.LogRecord(
            name='test',
            level=logging.WARNING,
            pathname='',
            lineno=0,
            msg='Test warning message',
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        # Check that requests.post was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check the URL
        self.assertEqual(call_args[0][0], webhook_urls['LOG'])
        
        # Check the JSON data
        json_data = call_args[1]['json']
        self.assertIn('WARNING', json_data['content'])
        self.assertIn('Test warning message', json_data['content'])
        self.assertIn('⚠️', json_data['content'])
    
    @patch('log.requests.post')
    def test_discord_handler_emit_info_no_send(self, mock_post):
        """Test DiscordHandler doesn't send INFO level messages"""
        webhook_urls = {'LOG': 'https://discord.com/api/webhooks/test'}
        handler = DiscordHandler(webhook_urls, level=logging.WARNING)
        
        # Create an INFO level log record
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test info message',
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        # Should not call requests.post for INFO level
        mock_post.assert_not_called()
    
    @patch('log.requests.post')
    def test_discord_handler_emit_no_log_webhook(self, mock_post):
        """Test DiscordHandler when LOG webhook is not configured"""
        webhook_urls = {'OTHER': 'https://discord.com/api/webhooks/test'}
        handler = DiscordHandler(webhook_urls, level=logging.WARNING)
        
        record = logging.LogRecord(
            name='test',
            level=logging.WARNING,
            pathname='',
            lineno=0,
            msg='Test warning message',
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        # Should not call requests.post when LOG webhook is not configured
        mock_post.assert_not_called()


class TestSendInstanceNotification(unittest.TestCase):
    """Test the send_instance_notification function"""
    
    @patch('log.requests.post')
    @patch('log.DISCORD_WEBHOOKS', {'INSTANCE': 'https://discord.com/api/webhooks/test_instance'})
    def test_send_instance_notification_success(self, mock_post):
        """Test successful instance notification sending"""
        mock_post.return_value.status_code = 200
        
        test_message = "Test notification message"
        send_instance_notification(test_message)
        
        # Check that requests.post was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check the URL
        self.assertEqual(call_args[0][0], 'https://discord.com/api/webhooks/test_instance')
        
        # Check the JSON data
        json_data = call_args[1]['json']
        self.assertIn('INSTANCE_NOTIFICATION', json_data['content'])
        self.assertIn(test_message, json_data['content'])
        self.assertIn('🔔', json_data['content'])
    
    @patch('log.requests.post')
    @patch('log.DISCORD_WEBHOOKS', {})
    def test_send_instance_notification_no_webhook(self, mock_post):
        """Test instance notification when INSTANCE webhook is not configured"""
        test_message = "Test notification message"
        send_instance_notification(test_message)
        
        # Should not call requests.post when INSTANCE webhook is not configured
        mock_post.assert_not_called()
    
    @patch('log.requests.post')
    @patch('log.DISCORD_WEBHOOKS', {'INSTANCE': 'https://discord.com/api/webhooks/test_instance'})
    def test_send_instance_notification_request_exception(self, mock_post):
        """Test instance notification when requests raises an exception"""
        mock_post.side_effect = Exception("Network error")
        
        test_message = "Test notification message"
        # Should not raise an exception
        send_instance_notification(test_message)
        
        # Verify that the request was attempted
        mock_post.assert_called_once()


class TestAnalyzeByHourEdgeCases(unittest.TestCase):
    """Test edge cases for analyze_by_hour function"""
    
    def test_analyze_by_hour_midnight_hours(self):
        """Test hour analysis with midnight hours"""
        timestamps = [
            datetime(2024, 1, 1, 0, 0, 0),  # Midnight
            datetime(2024, 1, 1, 23, 59, 59),  # Just before midnight
            datetime(2024, 1, 2, 0, 30, 0)  # Next day midnight
        ]
        counts = [10, 15, 12]
        
        result = analyze_by_hour(timestamps, counts)
        
        self.assertEqual(len(result[0]), 2)  # Two entries for hour 0
        self.assertEqual(len(result[23]), 1)  # One entry for hour 23
        self.assertEqual(result[0], [10, 12])
        self.assertEqual(result[23], [15])
    
    def test_analyze_by_hour_same_hour_multiple_days(self):
        """Test hour analysis with same hour across multiple days"""
        timestamps = [
            datetime(2024, 1, 1, 15, 0, 0),
            datetime(2024, 1, 2, 15, 0, 0),
            datetime(2024, 1, 3, 15, 0, 0)
        ]
        counts = [5, 8, 6]
        
        result = analyze_by_hour(timestamps, counts)
        
        self.assertEqual(len(result[15]), 3)
        self.assertEqual(result[15], [5, 8, 6])
    
    def test_analyze_by_hour_mismatched_lengths(self):
        """Test hour analysis with mismatched timestamp and count lengths"""
        timestamps = [
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 11, 0, 0)
        ]
        counts = [5]  # Only one count for two timestamps
        
        result = analyze_by_hour(timestamps, counts)
        
        # Should only process the first timestamp since zip stops at shortest
        self.assertEqual(len(result[10]), 1)
        self.assertEqual(result[10], [5])
        self.assertEqual(len(result[11]), 0)


class TestParseLogFileEdgeCases(unittest.TestCase):
    """Test edge cases for parse_log_file function"""
    
    def test_parse_log_file_malformed_timestamps(self):
        """Test parsing log file with malformed timestamps"""
        log_content = """2024-13-01 10:00:00 [INFO] [GROUP] グループのオンラインメンバー数:5
2024-01-32 11:00:00 [INFO] [GROUP] グループのオンラインメンバー数:8
2024-01-01 25:00:00 [INFO] [GROUP] グループのオンラインメンバー数:3"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write(log_content)
            temp_path = f.name
        
        try:
            timestamps, user_counts = parse_log_file(temp_path)
            # Should return empty lists since all timestamps are malformed
            self.assertEqual(timestamps, [])
            self.assertEqual(user_counts, [])
        finally:
            os.unlink(temp_path)
    
    def test_parse_log_file_non_numeric_counts(self):
        """Test parsing log file with non-numeric user counts"""
        log_content = """2024-01-01 10:00:00 [INFO] [GROUP] グループのオンラインメンバー数:abc
2024-01-01 11:00:00 [INFO] [GROUP] グループのオンラインメンバー数:5.5
2024-01-01 12:00:00 [INFO] [GROUP] グループのオンラインメンバー数:"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write(log_content)
            temp_path = f.name
        
        try:
            timestamps, user_counts = parse_log_file(temp_path)
            # The regex (\d+) will match "5" from "5.5", so we get one valid entry
            # "abc" and empty string won't match the regex pattern
            self.assertEqual(len(timestamps), 1)
            self.assertEqual(len(user_counts), 1)
            self.assertEqual(user_counts, [5])  # "5" extracted from "5.5"
            self.assertEqual(timestamps[0], datetime(2024, 1, 1, 11, 0, 0))
        finally:
            os.unlink(temp_path)
    
    def test_parse_log_file_mixed_valid_invalid(self):
        """Test parsing log file with mix of valid and invalid entries"""
        log_content = """2024-01-01 10:00:00 [INFO] [GROUP] グループのオンラインメンバー数:5
2024-13-01 11:00:00 [INFO] [GROUP] グループのオンラインメンバー数:8
2024-01-01 12:00:00 [INFO] [GROUP] グループのオンラインメンバー数:3
2024-01-01 13:00:00 [INFO] [GROUP] グループのオンラインメンバー数:abc"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write(log_content)
            temp_path = f.name
        
        try:
            timestamps, user_counts = parse_log_file(temp_path)
            # Should only return the valid entries
            self.assertEqual(len(timestamps), 2)
            self.assertEqual(len(user_counts), 2)
            self.assertEqual(user_counts, [5, 3])
            
            expected_times = [
                datetime(2024, 1, 1, 10, 0, 0),
                datetime(2024, 1, 1, 12, 0, 0)
            ]
            self.assertEqual(timestamps, expected_times)
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()