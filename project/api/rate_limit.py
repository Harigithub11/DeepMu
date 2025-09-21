from fastapi.middleware import middleware
from starlette.background import BackgroundTasks
from starlette.requests import Request
from starlette.responses import JSONResponse
import time

class RateLimitMiddleware:
    def __init__(self, app, limit=100, window=60):
        self.app = app
        self.limit = limit
        self.window = window
        self.requests = {}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        client_ip = scope.get("client", ("unknown",))[0]
        current_time = time.time()

        # Track requests
        self.requests[client_ip] = [
            t for t in self.requests.get(client_ip, [])
            if t > current_time - self.window
        ]

        if len(self.requests[client_ip]) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Try again later."}
            )

        self.requests[client_ip].append(current_time)
        await self.app(scope, receive, send)