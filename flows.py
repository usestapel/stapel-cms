"""Business flows of stapel-cms (stapel_core.flows).

The Flow objects live here; HTTP steps are attached in ``views.py`` with
``@flow_step``. Literals are the canonical English source texts.
"""
from stapel_core.flows import Flow

READ = Flow(
    "cms.read",
    title="Read the site's pages",
    description=(
        "A visitor opens a URL of the site; the frontend asks cms what lives at "
        "that path (a page, a post or a redirect) in the visitor's language, with "
        "fallback, and renders its blocks, SEO tags and menus. Reads are cached "
        "and answer 304 to a conditional request."
    ),
    actors=["Visitor (anonymous)"],
)
READ.human(order=0, note="The visitor opens a page of the site")

BLOG = Flow(
    "cms.blog",
    title="Read the blog",
    description=(
        "A visitor pages through the latest posts, filters by tag or month, opens "
        "a post, or subscribes to the RSS/Atom feed."
    ),
    actors=["Visitor (anonymous)"],
)

AUTHOR = Flow(
    "cms.author",
    title="Write and publish content",
    description=(
        "Staff write a page or post as a draft from typed blocks, preview it by a "
        "signed link, publish it now or schedule it, edit it while the published "
        "snapshot keeps serving, restore an older revision, and archive it. A "
        "moved page leaves a redirect behind."
    ),
    actors=["Staff editor"],
)
AUTHOR.action("cms.page.published", order=20, note="Publication is announced (cache purge, search, sitemap)")
AUTHOR.action("cms.page.unpublished", order=21, note="Archiving is announced")

SITE = Flow(
    "cms.site",
    title="Arrange the site",
    description="Staff edit the header and footer menus, tags and manual redirects.",
    actors=["Staff editor"],
)
SITE.action("cms.menu.changed", order=10, note="A menu change is announced")
