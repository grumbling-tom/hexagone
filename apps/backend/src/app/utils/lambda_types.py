"""Shared type definitions for AWS Lambda handlers.

This module provides common type definitions used across all Lambda handlers
in the Hexagone application. These types document the AWS Lambda runtime interface
and standardize response formats.
"""

from typing import Protocol, TypedDict


class LambdaContext(Protocol):
    """Protocol defining the AWS Lambda context interface.

    This protocol documents the subset of the Lambda context object used
    by Hexagone handlers. The actual context object provided by AWS Lambda
    has additional attributes not defined here.

    Attributes:
        aws_request_id: Unique identifier for the Lambda invocation.
        function_name: Name of the Lambda function being executed.

    See: https://docs.aws.amazon.com/lambda/latest/dg/python-context.html
    """

    aws_request_id: str
    function_name: str

    def get_remaining_time_in_millis(self) -> int:
        """Get remaining execution time in milliseconds.

        Returns:
            Milliseconds remaining before Lambda timeout.
        """
        ...


class LambdaResponse(TypedDict):
    """Type definition for Lambda response format.

    This standardizes the response structure across all Hexagone Lambda handlers.

    Attributes:
        statusCode: HTTP status code (200 for success, 500 for failure).
        body: Response body containing operation output or error message.
    """

    statusCode: int
    body: str
