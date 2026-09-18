"""The hosting computer can claim its own administrator account locally.

Never use a public/shared IP or a forwarded header to identify the owner.
Requests through a reverse proxy are deliberately ineligible for this shortcut.
"""
import ipaddress
from urllib.parse import urlsplit


def is_host_request(request):
    if not request.client:
        return False
    try:
        if not ipaddress.ip_address(request.client.host).is_loopback:
            return False
    except ValueError:
        return False
    if any(k.lower().startswith("x-forwarded-") or k.lower() in
           {"forwarded", "x-real-ip", "cf-connecting-ip", "true-client-ip"}
           for k in request.headers):
        return False
    # Also protects against DNS rebinding to the local listener.
    if request.url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        return False
    if request.headers.get("sec-fetch-site") not in (None, "same-origin", "none"):
        return False
    origin = request.headers.get("origin")
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme != request.url.scheme or parsed.netloc != request.url.netloc:
            return False
    return True
