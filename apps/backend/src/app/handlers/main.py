"""AWS Lambda handler for the FastAPI application.

Wraps the FastAPI application with Mangum to handle AWS API Gateway v2 events.
"""

import asyncio

from mangum import Mangum

from src.app.main import app

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

handler = Mangum(app, lifespan="off")
