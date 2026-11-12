"""Dataclass DTOs — the API models of stapel-cms (never ORM instances).

Built only by the presenters (``presenters.py``); views never instantiate
them. Nested shapes (blocks, SEO, alternates, menu trees) are plain dicts
already shaped by the service layer.
"""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ResolveDTO:
    """What lives at a public path: a page, a post or a redirect."""

    kind: str
    locale: str
    page: Optional[dict] = None
    post: Optional[dict] = None
    redirect: Optional[dict] = None


@dataclass
class PublicPostSummaryDTO:
    """One row of the blog list (no body)."""

    id: int
    locale: str
    slug: str
    path: str
    title: str
    excerpt: str
    cover: Optional[str]
    tags: list
    author_id: Optional[str]
    reading_time_minutes: int
    published_at: Optional[datetime.datetime]


@dataclass
class PublicPostDTO:
    """A published post with its body, as the public reads it."""

    id: int
    locale: str
    slug: str
    path: str
    title: str
    excerpt: str
    cover: Optional[str]
    tags: list
    author_id: Optional[str]
    reading_time_minutes: int
    published_at: Optional[datetime.datetime]
    blocks: list
    seo: dict
    updated_at: Optional[datetime.datetime]
    alternates: list


@dataclass
class PostArchiveDTO:
    """Months that have published posts, newest first."""

    months: list = field(default_factory=list)


@dataclass
class PublicTagListDTO:
    """Tags that have published posts, with counts."""

    items: list = field(default_factory=list)


@dataclass
class PublicMenuDTO:
    """A menu tree with targets resolved to live paths."""

    key: str
    title: str
    locale: str
    items: list = field(default_factory=list)


@dataclass
class StaffContentDTO:
    """A page's or post's working copy as the staff editor sees it."""

    id: int
    site: str
    locale: str
    translation_group: uuid.UUID
    slug: str
    path: str
    title: str
    blocks: list
    seo_title: str
    seo_description: str
    canonical_url: str
    og_image: str
    noindex: bool
    status: str
    version: int
    publish_at: Optional[datetime.datetime]
    published_at: Optional[datetime.datetime]
    last_published_at: Optional[datetime.datetime]
    archived_at: Optional[datetime.datetime]
    author_id: str
    updated_by_id: str
    live_revision: Optional[int]
    scheduled_revision: Optional[int]
    has_unpublished_changes: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    parent: Optional[int] = None
    template: str = ""
    excerpt: str = ""
    cover: str = ""
    tags: list = field(default_factory=list)
    reading_time_minutes: int = 1


@dataclass
class RevisionDTO:
    """One snapshot of a page or post."""

    number: int
    note: str
    created_by_id: str
    created_at: datetime.datetime
    is_live: bool
    is_scheduled: bool
    snapshot: dict


@dataclass
class PreviewTokenDTO:
    """A signed link to a draft's working copy."""

    token: str
    expires_at: datetime.datetime
    url: Optional[str]


@dataclass
class StaffTagDTO:
    """A blog tag as staff manage it."""

    id: int
    site: str
    locale: str
    slug: str
    name: str
    created_at: datetime.datetime


@dataclass
class StaffMenuDTO:
    """A menu with its raw item tree as staff edit it."""

    id: int
    site: str
    locale: str
    key: str
    title: str
    items: list
    updated_at: datetime.datetime


@dataclass
class StaffRedirectDTO:
    """One redirect, automatic or manual."""

    id: int
    site: str
    locale: str
    old_path: str
    new_path: str
    permanent: bool
    source: str
    created_by_id: str
    created_at: datetime.datetime


@dataclass
class BlockTypeListDTO:
    """Every registered block type with its data JSON Schema."""

    items: list = field(default_factory=list)
