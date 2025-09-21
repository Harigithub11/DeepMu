import os
from typing import List, Dict, Any
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

class DeepMuSecurityConfig:
    def __init__(self):
        self.domain = "deepmu.tech"
        self.allowed_origins = [
            f"https://{self.domain}",
            f"https://api.{self.domain}",
            f"https://admin.{self.domain}",
            f"https://docs.{self.domain}"
        ]

        # API Security
        self.api_security = {
            'require_https': True,
            'api_key_header': 'X-DeepMu-API-Key',
            'rate_limit_per_minute': 100,
            'max_request_size': '10MB',
            'allowed_content_types': [
                'application/json',
                'multipart/form-data',
                'application/pdf',
                'text/plain'
            ]
        }

        # JWT Configuration
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
        self.jwt_algorithm = 'HS256'
        self.jwt_expiration_hours = 24

        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token for deepmu.tech"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours)
        to_encode.update({"exp": expire, "domain": self.domain})

        return jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token for deepmu.tech"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            if payload.get("domain") != self.domain:
                raise jwt.InvalidTokenError("Invalid domain")
            return payload
        except jwt.PyJWTError:
            raise jwt.InvalidTokenError("Invalid token")

    def hash_password(self, password: str) -> str:
        """Hash password securely"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

# Global security config
security_config = DeepMuSecurityConfig()
