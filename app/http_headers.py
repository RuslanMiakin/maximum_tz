from app.config import get_settings


def get_http_headers(*, accept_json: bool = True) -> dict[str, str]:
    """Headers for outbound HTTP (Wikipedia requires descriptive User-Agent)."""
    headers = {"User-Agent": get_settings().http_user_agent}
    if accept_json:
        headers["Accept"] = "application/json"
    return headers
