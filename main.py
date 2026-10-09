import os
import time
import uuid

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


ALLOWED_ORIGIN = "https://dash-g9ck6j.example.com"
EMAIL = os.getenv("EMAIL", "REPLACE_WITH_YOUR_LOGGED_IN_EMAIL")

api = FastAPI()


@api.get("/stats")
def get_stats(values: str = Query(..., description="Comma-separated integers")):
    try:
        numbers = [int(item.strip()) for item in values.split(",")]
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail="values must be comma-separated integers"
        )

    if not numbers:
        raise HTTPException(status_code=400, detail="At least one integer is required")

    return {
        "email": EMAIL,
        "count": len(numbers),
        "sum": sum(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "mean": sum(numbers) / len(numbers),
    }


# CORS allows exactly the assigned website, not every website.
cors_app = CORSMiddleware(
    app=api,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# Outer ASGI middleware so its headers also appear on CORS preflight
# responses and responses rejected by the CORS layer.
class RequestMetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                elapsed = max(0.0, time.perf_counter() - start_time)
                headers = list(message.get("headers", []))
                headers.extend([
                    (b"x-request-id", request_id.encode("ascii")),
                    (b"x-process-time", f"{elapsed:.6f}".encode("ascii")),
                ])
                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_with_headers)


app = RequestMetricsMiddleware(cors_app)
