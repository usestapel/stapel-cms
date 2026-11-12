"""Signed preview tokens: a staff member shares the working copy of a draft.

The token names the object, not a version, so it keeps showing the latest
working copy while the editor saves. Forged or expired tokens answer 404
(a token cannot be probed).
"""
from __future__ import annotations

import datetime as dt

from django.core import signing
from django.utils import timezone

from ..errors import ERR_404_PREVIEW_INVALID
from . import CmsError

SALT = "stapel_cms.preview"


def mint(kind: str, obj_id: int) -> dict:
    from ..conf import cms_settings

    ttl = int(cms_settings.PREVIEW_TOKEN_TTL_SECONDS)
    token = signing.TimestampSigner(salt=SALT).sign_object({"k": kind, "i": int(obj_id)})
    template = str(cms_settings.PREVIEW_URL_TEMPLATE or "")
    url = template.replace("{token}", token) if template else None
    return {"token": token, "expires_at": timezone.now() + dt.timedelta(seconds=ttl), "url": url}


def read(token: str) -> tuple[str, int]:
    from ..conf import cms_settings

    try:
        data = signing.TimestampSigner(salt=SALT).unsign_object(
            str(token or ""), max_age=int(cms_settings.PREVIEW_TOKEN_TTL_SECONDS)
        )
        return str(data["k"]), int(data["i"])
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        raise CmsError(404, ERR_404_PREVIEW_INVALID) from None


__all__ = ["mint", "read"]
