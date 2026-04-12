from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_random,
    retry_if_exception_type,
    retry_if_result,
    AsyncRetrying,
)
import httpx

NETWORK_EXCEPTIONS = (httpx.ConnectError, httpx.RequestError, httpx.TimeoutException)


def is_rate_limited(response) -> bool:
    """Check if response indicates rate limiting (429)"""
    return response.status_code == 429


def is_server_error(response) -> bool:
    """Check if response indicates server error (5xx)"""
    return response.status_code >= 500


def check_response_retry(response) -> bool:
    """Check if response should trigger retry (429 or 5xx)"""
    return is_rate_limited(response) or is_server_error(response)
