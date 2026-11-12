"""The usual pages every site starts with, created as drafts.

Idempotent: a page whose path already exists is left alone. Nothing is
published — the placeholder text is for the owner to replace.
"""
from __future__ import annotations

from ..models import Page
from ..richtext import paragraph_doc
from . import content

SEED_PAGES = (
    ("about", "About us", "default", [
        "Tell visitors who you are, what you do and why it matters.",
    ]),
    ("contacts", "Contacts", "default", [
        "How to reach you: e-mail, phone, address and opening hours.",
    ]),
    ("terms", "Terms of service", "legal", [
        "The terms on which visitors use this site. Replace this text with your own terms.",
    ]),
    ("privacy", "Privacy policy", "legal", [
        "What personal data this site collects, why, and how visitors exercise their rights. "
        "Replace this text with your own policy.",
    ]),
)

FAQ_ITEMS = (
    ("How do I contact you?", "See the contacts page."),
    ("Where can I read the terms?", "On the terms of service page."),
)


def _blocks(slug: str, texts) -> list[dict]:
    return [{"type": "rich_text", "id": f"{slug}-body", "data": {"doc": paragraph_doc(*texts)}}]


def _faq_blocks() -> list[dict]:
    return [{"type": "faq", "id": "faq-main", "data": {"items": [
        {"question": q, "answer": paragraph_doc(a)} for q, a in FAQ_ITEMS
    ]}}]


def seed(site: str = "", locale: str | None = None, user=None) -> list[str]:
    """Create the missing seed pages; return the paths created."""
    from ..conf import cms_settings

    locale = locale or str(cms_settings.DEFAULT_LOCALE)
    templates = list(cms_settings.PAGE_TEMPLATES or [])
    created = []
    plan = [(slug, title, tpl, _blocks(slug, texts)) for slug, title, tpl, texts in SEED_PAGES]
    plan.append(("faq", "Frequently asked questions", "faq", _faq_blocks()))
    for slug, title, template, blocks in plan:
        if Page.objects.filter(site=site, locale=locale, path=f"/{slug}").exists():
            continue
        content.create("page", user, {
            "site": site, "locale": locale, "slug": slug, "parent": None, "title": title,
            "template": template if template in templates else (templates[0] if templates else "default"),
            "blocks": blocks,
        })
        created.append(f"/{slug}")
    return created


__all__ = ["SEED_PAGES", "seed"]
