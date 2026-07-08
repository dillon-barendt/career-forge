SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-notion-signature",
    "x-hub-signature",
    "x-hub-signature-256",
    "x-signature",
}


def normalize_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key.lower(): value for key, value in headers.items()}


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    normalized = normalize_headers(headers)
    return {
        key: "[redacted]" if key in SENSITIVE_HEADER_NAMES else value
        for key, value in normalized.items()
    }
