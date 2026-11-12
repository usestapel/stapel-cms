"""The one URL rule every link in cms content passes.

A link is rendered into an ``href`` by every client the content reaches
(web, e-mail, mobile). The rule is an allowlist of prefixes checked on the
raw value, never a denylist of schemes: whitespace and control characters
are refused outright (``java\\tscript:`` is ``javascript:`` to a browser),
and anything not starting with an allowed prefix fails — which covers
``javascript:``, ``data:``, ``vbscript:``, entity-encoded schemes
(``&#106;avascript:``) and protocol-relative ``//host`` without naming them.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

#: Prefixes a link may start with, compared case-insensitively.
SAFE_PREFIXES = ("https://", "http://", "mailto:", "tel:", "/", "#")

#: A stapel-cdn media reference: ``<type>/<id>``.
MEDIA_REF_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}/[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")

_FORBIDDEN_CHARS = re.compile(r"[\x00-\x20\x7f-\x9f\\<>\"'`]")


def is_safe_url(value: str) -> bool:
    """May ``value`` be rendered as a link target?"""
    if not isinstance(value, str) or not value:
        return False
    if _FORBIDDEN_CHARS.search(value):
        return False
    lowered = value.lower()
    if lowered.startswith("//"):
        return False
    if not lowered.startswith(SAFE_PREFIXES):
        return False
    if lowered.startswith(("https://", "http://")):
        try:
            parts = urlsplit(value)
        except ValueError:
            return False
        if not parts.hostname or "@" in (parts.netloc or ""):
            return False
    return True


def embed_host_allowed(url: str, allowed_hosts) -> bool:
    """Is ``url`` an https URL on exactly one of ``allowed_hosts``?"""
    if not is_safe_url(url) or not url.lower().startswith("https://"):
        return False
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    if port not in (None, 443):
        return False
    host = (parts.hostname or "").lower().rstrip(".")
    return host in {str(h).lower().rstrip(".") for h in allowed_hosts or ()}


def is_media_ref(value: str) -> bool:
    return isinstance(value, str) and bool(MEDIA_REF_RE.match(value))


__all__ = ["MEDIA_REF_RE", "SAFE_PREFIXES", "embed_host_allowed", "is_media_ref", "is_safe_url"]
