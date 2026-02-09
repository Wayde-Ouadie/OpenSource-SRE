"""Resilient HTTP client with retries and timeouts."""
import httpx
from typing import Optional


def create_http_client(
    timeout: float = 5.0,
    retries: int = 3,
    base_url: Optional[str] = None
) -> httpx.AsyncClient:
    """Create an HTTP client with retry logic.
    
    Args:
        timeout: Request timeout in seconds
        retries: Number of retry attempts
        base_url: Base URL for all requests
    
    Returns:
        Configured AsyncClient instance
    """
    transport = httpx.AsyncHTTPTransport(retries=retries)
    
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        transport=transport,
        base_url=base_url,
        follow_redirects=True,
    )


async def safe_http_call(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs
) -> tuple[Optional[dict], Optional[str]]:
    """Make a safe HTTP call that returns (data, error).
    
    Args:
        client: HTTP client instance
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        **kwargs: Additional arguments for the request
    
    Returns:
        Tuple of (response_data, error_message)
    """
    try:
        response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json(), None
    except httpx.HTTPStatusError as e:
        return None, f"HTTP {e.response.status_code}: {e.response.text[:100]}"
    except httpx.RequestError as e:
        return None, f"Request failed: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"
