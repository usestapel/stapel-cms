"""Anchor paginators (every list is anchor-paginated; R013 by construction).

- Staff lists walk ``-id`` with the id as a string anchor.
- The public blog walks ``(published_at, id)`` newest first — a keyset on two
  columns, because many posts can share a date. The anchor is
  ``"<epoch microseconds>_<id>"`` (nothing to escape in a query string).
"""
from __future__ import annotations

import datetime as dt

from django.db.models import Q
from rest_framework.response import Response
from stapel_core.django.api.pagination import AnchorPagination

UTC = dt.timezone.utc


def _without_anchor(request, param):
    """A bad anchor reads as no anchor (the head of the list), never a 500."""

    class _Request:
        def __init__(self, inner):
            self._inner = inner
            self.query_params = inner.query_params.copy()
            self.query_params.pop(param, None)

        def __getattr__(self, name):
            return getattr(self._inner, name)

    return _Request(request)


class StaffAnchorPagination(AnchorPagination):
    page_size = 50
    max_page_size = 200
    anchor_field = "id"
    anchor_type = "string"
    ordering = "-id"

    def paginate_queryset(self, queryset, request, view=None):
        anchor = request.query_params.get(self.anchor_param)
        if anchor is not None and not anchor.isdigit():
            request = _without_anchor(request, self.anchor_param)
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        for key in ("next_anchor", "prev_anchor"):
            if response.data[key] is not None:
                response.data[key] = str(response.data[key])
        return response


def encode_anchor(when: dt.datetime, pk: int) -> str:
    delta = when.astimezone(UTC) - dt.datetime(1970, 1, 1, tzinfo=UTC)
    micros = (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds
    return f"{micros}_{pk}"


def decode_anchor(raw: str | None):
    if not raw or "_" not in raw:
        return None
    micros, _, pk = raw.partition("_")
    if not (micros.lstrip("-").isdigit() and pk.isdigit()):
        return None
    return dt.datetime(1970, 1, 1, tzinfo=UTC) + dt.timedelta(microseconds=int(micros)), int(pk)


class PostAnchorPagination(AnchorPagination):
    """Published posts, newest first, keyset on ``(published_at, id)``."""

    page_size = 12
    max_page_size = 50
    anchor_type = "string"
    ordering = "-published_at"

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        self.limit = self._get_limit(request)
        anchor = decode_anchor(request.query_params.get(self.anchor_param))
        backward = request.query_params.get(self.direction_param) == "prev" and anchor is not None
        if anchor is not None:
            when, pk = anchor
            if backward:
                queryset = queryset.filter(Q(published_at__gt=when) | Q(published_at=when, id__gt=pk))
            else:
                queryset = queryset.filter(Q(published_at__lt=when) | Q(published_at=when, id__lt=pk))
        queryset = queryset.order_by(*(("published_at", "id") if backward else ("-published_at", "-id")))
        items = list(queryset[: self.limit + 1])
        more = len(items) > self.limit
        items = items[: self.limit]
        if backward:
            items.reverse()
            self._has_prev, self._has_next = more, True
        else:
            self._has_next, self._has_prev = more, anchor is not None
        self._items = items
        return items

    def page_envelope(self, data) -> dict:
        items = self._items
        return {
            "items": data,
            "next_anchor": encode_anchor(items[-1].published_at, items[-1].pk) if items and self._has_next else None,
            "prev_anchor": encode_anchor(items[0].published_at, items[0].pk) if items and self._has_prev else None,
            "has_next": self._has_next,
            "has_prev": self._has_prev,
            "count": len(data),
        }

    def get_paginated_response(self, data):
        return Response(self.page_envelope(data))
