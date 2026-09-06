"""
Flask application for HTML processing service.

This module provides a REST API for processing MediaWiki HTML through
the Content Translation pipeline. It exposes endpoints for HTML text
processing and health checks.

"""

from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, Response, jsonify, render_template, request

from .lib.processor import process_html

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """Exception raised when HTML processing fails."""

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        """
        Initialize processing error.

        Args:
            message: Human-readable error message.
            original_error: The original exception that caused this error.
        """
        super().__init__(message)
        self.message = message
        self.original_error = original_error


def validate_request(data: dict[str, Any] | None) -> tuple[bool, str]:
    """
    Validate the incoming request data.

    Args:
        data: Parsed JSON data from the request.

    Returns:
        Tuple of (is_valid, error_message). If is_valid is True,
        error_message will be empty.

    Examples:
        >>> validate_request(None)
        (False, 'Invalid JSON payload')

        >>> validate_request({})
        (False, 'Missing required field: html')

        >>> validate_request({'html': '   '})
        (False, 'HTML content is empty or contains only whitespace')

        >>> validate_request({'html': '<p>Hello</p>'})
        (True, '')
    """
    if data is None:
        return False, "Invalid JSON payload"

    if "html" not in data:
        return False, "Missing required field: html"

    source_html = data.get("html", "")

    if not isinstance(source_html, str):
        return False, "HTML field must be a string"

    if not source_html or not source_html.strip():
        return False, "HTML content is empty or contains only whitespace"

    return True, ""


def create_error_response(message: str, status_code: int) -> tuple[Response, int]:
    """
    Create a standardized JSON error response.

    Args:
        message: Error message to include in response.
        status_code: HTTP status code.

    Returns:
        Tuple of (Response object, status code).
    """
    return jsonify({"result": message, "success": False}), status_code


def create_success_response(result: str) -> tuple[Response, int]:
    """
    Create a standardized JSON success response.

    Args:
        result: Processed HTML content.

    Returns:
        Tuple of (Response object, status code).
    """
    return jsonify({"result": result, "success": True}), 200


def process_text() -> tuple[Response, int]:
    """
    Process HTML text through the CX pipeline.

    This endpoint accepts MediaWiki HTML (Parsoid format) and returns
    segmented HTML with proper IDs and metadata suitable for translation.

    Request:
        Method: POST
        Content-Type: application/json
        Body: {"html": "<html>...</html>"}

    Response:
        Success (200):
            {"result": "<processed html>", "success": true}

        Error (4xx/5xx):
            {"result": "error message", "success": false}

    Status Codes:
        200: Successful processing
        400: Invalid request (missing/invalid JSON, empty HTML)
        413: Payload too large
        415: Unsupported media type
        500: Internal server error

    Raises:
        No exceptions are raised; all errors are caught and returned
        as JSON error responses.

    Examples:
        Using curl::

            $ curl -X POST http://localhost:8000/textp \\
                -H "Content-Type: application/json" \\
                -d '{"html": "<p>Hello world</p>"}'

    Note:
        The endpoint has a maximum content length limit to prevent
        denial-of-service attacks.
    """
    # Validate content type
    if not request.is_json:  # Check if the request is in JSON format
        logger.warning("Request rejected: Content-Type is not application/json")
        return create_error_response("Content-Type must be application/json", 415)

    # Parse and validate JSON
    try:
        data = request.get_json(silent=True)  # Attempt to parse JSON data from request
    except Exception as e:
        logger.warning(f"JSON parsing failed: {e}")  # Log any parsing errors
        return create_error_response("Invalid JSON payload", 400)

    # Validate request data
    is_valid, error_message = validate_request(data)  # Check if the request data is valid
    if not is_valid:
        logger.warning(f"Request validation failed: {error_message}")
        return create_error_response(error_message, 400)

    # Extract HTML from the request data
    source_html = data["html"]  # pyright: ignore[reportOptionalSubscript]

    # Process the HTML
    try:
        logger.info(f"Processing HTML request ({len(source_html)} bytes)")  # Log the processing start
        processed_text = process_html(source_html)  # Process the HTML content
        logger.info("HTML processing completed successfully")  # Log successful processing
        return create_success_response(processed_text)  # Return the processed HTML

    except ProcessingError as e:  # Handle processing-specific errors
        logger.error(f"Processing error: {e.message}")  # Log processing error
        return create_error_response(e.message, 500)  # Return error response

    except Exception as e:  # Handle any unexpected errors
        # Log the full error internally but return a generic message
        logger.error(f"Unexpected error processing HTML: {e}", exc_info=True)
        return create_error_response("An internal error occurred while processing the HTML", 500)


class HtmltoSegmentsRoutes:
    def __init__(self, bp: Blueprint) -> None:
        self.bp = bp
        self._setup_routes()

    def _setup_routes(self) -> None:
        routes = [
            ("/", "POST", self.process_text),
            ("/", "GET", self.index),
        ]
        for rule, method, target in routes:
            self.bp.route(rule, methods=[method])(target)

    def process_text(self):
        return process_text()

    def index(self) -> str:
        return render_template(
            "html_to_segments/index.html",
        )


__all__ = [
    "HtmltoSegmentsRoutes",
]
