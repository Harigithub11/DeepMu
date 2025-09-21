import os
from fastapi.middleware import middleware
from starlette.requests import Request
from starlette.responses import Response

class SSLMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Force HTTPS redirect
            if not scope.get("headers", b"").startswith(b"X-Forwarded-Proto: https"):
                return Response(
                    status_code=301,
                    headers={"Location": "https://" + scope["server"][0] + scope["path"]},
                )
        return await self.app(scope, receive, send)