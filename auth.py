import requests
import logging

class KreedoAuth:
    def __init__(self):
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

    def login_with_token(self, url, token):
        """
        Login using a provided token.
        This usually means setting the Authorization header for future requests.
        """
        self.logger.info(f"Attempting login with token to {url}")
        self.session.headers.update({"Authorization": f"JWT {token}"})
        
        # Verify the token works by making a lightweight request if possible
        # For now, we assume it's valid if provided, or we could add a verify step here.
        try:
            # Example verification (endpoint might differ based on actual API)
            # response = self.session.get(f"{url}/api/user/profile")
            # response.raise_for_status()
            self.logger.info("Token login configured.")
            return True
        except Exception as e:
            self.logger.error(f"Token login failed: {e}")
            return False

    def login_with_credentials(self, url, user_id, password):
        """
        Login using user_id and password to obtain a token/session.
        """
        self.logger.info(f"Attempting login with credentials to {url}")
        login_endpoint = f"{url}/users/login" # Adjust endpoint as needed
        payload = {
            "email": user_id,
            "password": password
        }
        
        try:
            response = self.session.post(login_endpoint, json=payload)
            response.raise_for_status()
            
            data = response.json()
            # Handle nested data structure from Kreedo API
            if "data" in data and isinstance(data["data"], dict):
                token = data["data"].get("token")
            else:
                token = data.get("token") or data.get("access_token")
            
            if token:
                self.session.headers.update({"Authorization": f"JWT {token}"})
                self.logger.info("Credential login successful.")
                return token
            else:
                self.logger.error(f"Login successful but no token found. Response: {data}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Credential login failed: {e}")
            return False

    def validate_token(self, url, token):
        """
        Validate the token by making a request to a protected endpoint.
        Returns True if valid, False otherwise.
        """
        self.logger.info("Validating token...")
        try:
            # Using 'users/logged_in_user_detail' as identified in api.config
            # The base URL passed is likely ending in /users, so we just append /logged_in_user_detail
            headers = {"Authorization": f"JWT {token}"}
            response = self.session.get(f"{url}/users/logged_in_user_detail", headers=headers)
            response.raise_for_status()
            self.logger.info("Token is valid.")
            return True
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Token validation failed: {e}")
            return False
