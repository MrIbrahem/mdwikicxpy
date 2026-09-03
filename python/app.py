"""
Flask application for HTML processing service.

This module provides a REST API for processing MediaWiki HTML through
the Content Translation pipeline. It exposes endpoints for HTML text
processing and health checks.

Endpoints:
    POST /textp - Process HTML through the CX pipeline
    GET /health - Health check endpoint

Security Considerations:
    - Input size is limited to prevent DoS attacks
    - Content-Type validation is enforced
    - Error messages are sanitized before returning to clients

Example:
    Running the development server::

        $ python app.py

    Production deployment with gunicorn::

        $ gunicorn -w 4 -b 0.0.0.0:8000 app:app

Author: mdwikicxpy
License: GPL-3.0
Version: 1.0.0
"""

from __future__ import annotations

import logging
import os
from typing import Any

from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from lib.processor import process_html

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Security constants
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB maximum HTML size
MAX_JSON_SIZE = 15 * 1024 * 1024  # 15MB maximum JSON payload

app = Flask(__name__)
CORS(app)

# Set maximum content length for the application
app.config["MAX_CONTENT_LENGTH"] = MAX_JSON_SIZE


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

    if len(source_html) > MAX_CONTENT_LENGTH:
        return False, f"HTML content exceeds maximum allowed size ({MAX_CONTENT_LENGTH // (1024*1024)}MB)"

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


@app.route("/textp", methods=["POST"])
@app.route("/HtmltoSegments", methods=["POST"])
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
    if not request.is_json:
        logger.warning("Request rejected: Content-Type is not application/json")
        return create_error_response("Content-Type must be application/json", 415)

    # Parse and validate JSON
    try:
        data = request.get_json(silent=True)
    except Exception as e:
        logger.warning(f"JSON parsing failed: {e}")
        return create_error_response("Invalid JSON payload", 400)

    # Validate request data
    is_valid, error_message = validate_request(data)
    if not is_valid:
        logger.warning(f"Request validation failed: {error_message}")
        return create_error_response(error_message, 400)

    source_html = data["html"]

    # Process the HTML
    try:
        logger.info(f"Processing HTML request ({len(source_html)} bytes)")
        processed_text = process_html(source_html)
        logger.info("HTML processing completed successfully")
        return create_success_response(processed_text)

    except ProcessingError as e:
        logger.error(f"Processing error: {e.message}")
        return create_error_response(e.message, 500)

    except Exception as e:
        # Log the full error internally but return a generic message
        logger.error(f"Unexpected error processing HTML: {e}", exc_info=True)
        return create_error_response("An internal error occurred while processing the HTML", 500)


@app.route("/health", methods=["GET"])
def health() -> tuple[Response, int]:
    """
    Health check endpoint for monitoring and load balancers.

    This endpoint returns a simple status indicating the service is
    operational. It can be used by:
    - Container orchestration systems (Kubernetes, Docker Swarm)
    - Load balancers for health checks
    - Monitoring systems

    Request:
        Method: GET
        Content-Type: None required

    Response:
        Success (200):
            {"status": "ok"}

    Examples:
        Using curl::

            $ curl http://localhost:8000/health
            {"status": "ok"}

    Note:
        This endpoint performs no actual processing and should always
        return quickly. For more comprehensive health checks that verify
        dependencies, consider adding a /health/detailed endpoint.
    """
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    logger.info(f"Starting Flask server on port {port} (debug={debug})")
    app.run(host="0.0.0.0", port=port, debug=debug)
