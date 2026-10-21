import time
import socket
import ipaddress
from urllib.parse import urlparse
import requests
from flask import current_app, has_app_context
from backend.config import Config


class SSRFValidationError(ValueError):
    """Raised when a health check target violates SSRF security policies."""
    pass


def is_ip_blocked(ip_str: str) -> bool:
    """
    Checks if an IP address belongs to private, loopback, link-local,
    multicast, or cloud metadata ranges (e.g. AWS 169.254.169.254).
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True

    # Check standard Python ipaddress restrictions
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True

    # Explicit check for AWS EC2 instance metadata service (IMDSv1/v2)
    # and link-local IPv4/IPv6 blocks
    if ip_str.startswith("169.254."):
        return True

    return False


def validate_url_security(url: str, allow_local: bool = False):
    """
    Validates that a URL is safe to query:
    1. Scheme must be http or https
    2. Hostname cannot be empty or 'localhost'
    3. Resolved IP addresses must not be internal/private/loopback/cloud metadata
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFValidationError("Health check URL scheme must be http or https.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("Invalid health check URL: missing hostname.")

    if allow_local:
        return

    # Check literal hostname against known localhost aliases
    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise SSRFValidationError("Health checks targeting localhost/loopback addresses are blocked for security.")

    # Revalidate DNS resolution to prevent DNS rebinding to internal addresses
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SSRFValidationError(f"Could not resolve hostname '{hostname}': {str(e)}")

    for info in addr_info:
        ip_addr = info[4][0]
        if is_ip_blocked(ip_addr):
            raise SSRFValidationError(
                f"Health checks targeting private/internal/cloud metadata address ({ip_addr}) are blocked for security."
            )


def perform_health_check(url: str, expected_status_code: int = 200, allow_local: bool = None) -> dict:
    """
    Executes a health check against the configured URL.
    Returns a dict with:
      - status: 'HEALTHY' or 'UNHEALTHY'
      - http_status_code: int or None
      - response_time_ms: float or None
      - error_message: str or None
    """
    if allow_local is None:
        if has_app_context() and "ALLOW_LOCAL_HEALTHCHECKS" in current_app.config:
            allow_local = current_app.config["ALLOW_LOCAL_HEALTHCHECKS"]
        else:
            allow_local = Config.ALLOW_LOCAL_HEALTHCHECKS

    # 1. Security validation
    try:
        validate_url_security(url, allow_local=allow_local)
    except SSRFValidationError as e:
        return {
            "status": "UNHEALTHY",
            "http_status_code": None,
            "response_time_ms": None,
            "error_message": f"Security violation: {str(e)}",
        }
    except Exception as e:
        return {
            "status": "UNHEALTHY",
            "http_status_code": None,
            "response_time_ms": None,
            "error_message": f"URL validation error: {str(e)}",
        }

    # 2. Perform HTTP request with timeout and response size capping
    timeout = Config.HEALTH_CHECK_TIMEOUT_SECONDS
    max_bytes = Config.MAX_RESPONSE_SIZE_BYTES
    start_time = time.perf_counter()

    try:
        # Use stream=True to guard against huge payload memory exhaustion
        # allow_redirects=False prevents redirect-based SSRF bypass
        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=False,
            stream=True,
            headers={"User-Agent": "DeployGuard-HealthCheck/1.0"}
        )

        # Read up to max_bytes
        _ = response.raw.read(max_bytes + 1)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        status_code = response.status_code
        if status_code == expected_status_code:
            return {
                "status": "HEALTHY",
                "http_status_code": status_code,
                "response_time_ms": elapsed_ms,
                "error_message": None,
            }
        else:
            return {
                "status": "UNHEALTHY",
                "http_status_code": status_code,
                "response_time_ms": elapsed_ms,
                "error_message": f"Expected HTTP status {expected_status_code}, but received {status_code}.",
            }

    except requests.exceptions.Timeout:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": "UNHEALTHY",
            "http_status_code": None,
            "response_time_ms": elapsed_ms,
            "error_message": f"Request timed out after {timeout} seconds.",
        }
    except requests.exceptions.ConnectionError as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": "UNHEALTHY",
            "http_status_code": None,
            "response_time_ms": elapsed_ms,
            "error_message": f"Connection failed: {str(e)}",
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": "UNHEALTHY",
            "http_status_code": None,
            "response_time_ms": elapsed_ms,
            "error_message": f"Health check failed: {str(e)}",
        }
