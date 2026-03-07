"""File upload processing handler."""

from typing import Any

from src.app.utils.lambda_types import LambdaContext, LambdaResponse


def handler(
    event: dict[str, Any],
    context: LambdaContext,  # noqa: ARG001
) -> LambdaResponse:
    print("File upload handler invoked!")
    print(f"Event: {event}")
    return {"statusCode": 200, "body": "OK"}
