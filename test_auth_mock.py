import unittest
from unittest.mock import MagicMock, patch
import requests
from auth import KreedoAuth

class TestKreedoAuth(unittest.TestCase):
    def setUp(self):
        self.auth = KreedoAuth()

    def test_login_with_token(self):
        # Test that token login sets the header
        url = "http://example.com"
        token = "fake-token"
        
        # We are not mocking the verification request in auth.py yet as it was commented out,
        # but if we did, we would mock session.get here.
        
        success = self.auth.login_with_token(url, token)
        self.assertTrue(success)
        self.assertEqual(self.auth.session.headers["Authorization"], f"Bearer {token}")

    @patch('requests.Session.post')
    def test_login_with_credentials_success(self, mock_post):
        url = "http://example.com"
        user = "user"
        password = "password"
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "returned-token"}
        mock_post.return_value = mock_response
        
        success = self.auth.login_with_credentials(url, user, password)
        
        self.assertTrue(success)
        self.assertEqual(self.auth.session.headers["Authorization"], "Bearer returned-token")
        mock_post.assert_called_with(f"{url}/login", json={"username": user, "password": password})

    @patch('requests.Session.post')
    def test_login_with_credentials_failure(self, mock_post):
        url = "http://example.com"
        user = "user"
        password = "wrong-password"
        
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Unauthorized")
        mock_post.return_value = mock_response
        
        success = self.auth.login_with_credentials(url, user, password)
        
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
