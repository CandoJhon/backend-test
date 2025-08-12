import aiohttp
import jwt
import os
import logging
from typing import Dict, Optional
from urllib.parse import urlencode
import json

logger = logging.getLogger(__name__)

class AppIDAuth:
    def __init__(self, region: str, tenant_id: str, client_id: str, secret: str):
        self.region = region
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.secret = secret
        
        # IBM App ID endpoints
        self.base_url = f"https://{region}.appid.cloud.ibm.com"
        self.oauth_server_url = f"{self.base_url}/oauth/v4/{tenant_id}"
        self.management_url = f"{self.base_url}/management/v4/{tenant_id}"
        
        # Cache for public keys
        self._public_keys = None
        
        logger.info(f"Initialized IBM App ID auth for tenant: {tenant_id}")
    
    def get_login_url(self, redirect_uri: str = None, state: str = None) -> str:
        """Generate IBM App ID login URL"""
        if not redirect_uri:
            redirect_uri = os.getenv("APPID_REDIRECT_URI", "http://localhost:8080/auth/callback")
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "openid profile email"
        }
        
        if state:
            params["state"] = state
            
        return f"{self.oauth_server_url}/authorization?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str = None) -> Dict:
        """Exchange authorization code for tokens"""
        if not redirect_uri:
            redirect_uri = os.getenv("APPID_REDIRECT_URI", "http://localhost:8080/auth/callback")
        
        token_url = f"{self.oauth_server_url}/token"
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.secret
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data, headers=headers) as response:
                if response.status == 200:
                    tokens = await response.json()
                    logger.info("Successfully exchanged code for tokens")
                    return tokens
                else:
                    error_text = await response.text()
                    logger.error(f"Token exchange failed: {response.status} - {error_text}")
                    raise Exception(f"Token exchange failed: {response.status}")
    
    async def get_public_keys(self) -> Dict:
        """Get IBM App ID public keys for token verification"""
        if self._public_keys:
            return self._public_keys
            
        keys_url = f"{self.oauth_server_url}/publickeys"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(keys_url) as response:
                if response.status == 200:
                    self._public_keys = await response.json()
                    return self._public_keys
                else:
                    raise Exception(f"Failed to get public keys: {response.status}")
    
    async def verify_token(self, token: str) -> Dict:
        """Verify and decode IBM App ID token"""
        try:
            # Get public keys
            public_keys = await self.get_public_keys()
            
            # Decode token header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            key_id = unverified_header.get("kid")
            
            # Find the right public key
            public_key = None
            for key in public_keys.get("keys", []):
                if key.get("kid") == key_id:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                    break
            
            if not public_key:
                raise Exception("Public key not found")
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.oauth_server_url
            )
            
            logger.info(f"Token verified for user: {payload.get('sub')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.error("Token has expired")
            raise Exception("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise Exception("Invalid token")
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise Exception(f"Token verification failed: {e}")
    
    async def get_user_info(self, access_token: str) -> Dict:
        """Get user information using access token"""
        userinfo_url = f"{self.oauth_server_url}/userinfo"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(userinfo_url, headers=headers) as response:
                if response.status == 200:
                    user_info = await response.json()
                    logger.info(f"Retrieved user info for: {user_info.get('sub')}")
                    return user_info
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to get user info: {response.status} - {error_text}")
                    raise Exception(f"Failed to get user info: {response.status}")
    
    async def refresh_token(self, refresh_token: str) -> Dict:
        """Refresh access token using refresh token"""
        token_url = f"{self.oauth_server_url}/token"
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.secret
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data, headers=headers) as response:
                if response.status == 200:
                    tokens = await response.json()
                    logger.info("Successfully refreshed tokens")
                    return tokens
                else:
                    error_text = await response.text()
                    logger.error(f"Token refresh failed: {response.status} - {error_text}")
                    raise Exception(f"Token refresh failed: {response.status}")