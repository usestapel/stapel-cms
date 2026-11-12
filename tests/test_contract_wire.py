"""Every response body the committed schema declares is the body the views send.

The operation list is DERIVED from ``docs/schema.json``: an operation with a
declared JSON 2xx body and no recipe here fails loudly. Every body is
validated against its declared schema (OAS ``nullable`` honoured), and each
read is driven in a populated and an empty state.
"""
import copy
import json
from pathlib import Path

import jsonschema
import pytest

from .helpers import in_future, make_page, make_post, publish, rich, transition

REPO = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((REPO / "docs" / "schema.json").read_text())
V1 = "/cms/api/v1"

pytestmark = pytest.mark.django_db


def _json_schema(node):
    if isinstance(node, list):
        return [_json_schema(item) for item in node]
    if not isinstance(node, dict):
        return node
    rebuilt = {k: _json_schema(v) for k, v in node.items() if k != "nullable"}
    if node.get("nullable"):
        return {"anyOf": [rebuilt, {"type": "null"}]}
    return rebuilt


def _validator(body_schema):
    root = copy.deepcopy(body_schema)
    root["components"] = copy.deepcopy(SCHEMA["components"])
    return jsonschema.Draft202012Validator(_json_schema(root))


def _operations():
    ops = []
    for path, methods in SCHEMA["paths"].items():
        for method, op in methods.items():
            for code, response in op.get("responses", {}).items():
                body = response.get("content", {}).get("application/json", {}).get("schema")
                if body is not None and code.startswith("2"):
                    ops.append((method.upper(), path, int(code), body))
    return sorted(ops, key=lambda o: (o[1], o[0], o[2]))


OPERATIONS = _operations()


def _url(path, **params):
    for name, value in params.items():
        path = path.replace("{%s}" % name, str(value))
    assert "{" not in path, f"unfilled path parameter in {path}"
    return path



def _live_page(c, slug="about", **kw):
    return publish(c, "page", make_page(c, slug, **kw)["id"])


def _live_post(c, slug="hello", **kw):
    return publish(c, "post", make_post(c, slug, **kw)["id"])


def _full_page(c):
    """A page exercising every optional public field (alternates, breadcrumbs, SEO)."""
    parent = _live_page(c, "about", title="About")
    child = make_page(c, "team", parent=parent["id"], seo_description="d", canonical_url="https://example.com/t",
                      og_image="page/og")
    publish(c, "page", child["id"])
    de = c.post(f"{V1}/staff/pages/{child['id']}/variants/", {"locale": "de"}, format="json").json()
    publish(c, "page", de["id"])
    return child


def r_resolve(env):
    c = env.staff
    _full_page(c)
    _live_post(c, "hello")
    c.post(f"{V1}/staff/redirects/", {"locale": "en", "old_path": "/old", "new_path": "/about"}, format="json")
    a = env.anon
    return [a.get(f"{V1}/public/resolve/", {"path": p}) for p in ("/about/team", "/blog/hello", "/old")], []


def r_preview(env):
    page = make_page(env.staff, "draft")
    post = make_post(env.staff, "draft-post")
    out = []
    for kind, obj in (("pages", page), ("posts", post)):
        token = env.staff.post(f"{V1}/staff/{kind}/{obj['id']}/preview-token/").json()["token"]
        out.append(env.anon.get(f"{V1}/public/preview/", {"token": token}))
    return out, []


def r_posts(env):
    empty = env.anon.get(f"{V1}/public/posts/")
    tag = env.staff.post(f"{V1}/staff/tags/", {"locale": "en", "slug": "news", "name": "News"},
                         format="json").json()
    for i in range(3):
        _live_post(env.staff, f"p{i}", tags=[tag["id"]], cover="post/c1")
    return [env.anon.get(f"{V1}/public/posts/", {"limit": 2})], [empty]


def r_post(env):
    _live_post(env.staff, "hello", cover="post/c1")
    return [env.anon.get(f"{V1}/public/posts/hello/")], []


def r_archive(env):
    empty = env.anon.get(f"{V1}/public/post-archive/", {"locale": "de"})
    _live_post(env.staff, "hello")
    return [env.anon.get(f"{V1}/public/post-archive/")], [empty]


def r_tags(env):
    empty = env.anon.get(f"{V1}/public/tags/", {"locale": "de"})
    tag = env.staff.post(f"{V1}/staff/tags/", {"locale": "en", "slug": "news", "name": "News"},
                         format="json").json()
    _live_post(env.staff, "hello", tags=[tag["id"]])
    return [env.anon.get(f"{V1}/public/tags/")], [empty]


def _menu(env):
    page = _live_page(env.staff, "menu-target")
    post = _live_post(env.staff, "menu-post")
    return env.staff.post(f"{V1}/staff/menus/", {"locale": "en", "key": "header", "title": "Header", "items": [
        {"label": "P", "target_type": "page", "page": page["id"], "children": [
            {"label": "U", "target_type": "url", "url": "https://example.com"}]},
        {"label": "B", "target_type": "post", "post": post["id"]},
        {"label": "R", "target_type": "route", "route": "account.root", "route_params": {"x": 1}}]}, format="json")


def r_menu(env):
    _menu(env)
    return [env.anon.get(f"{V1}/public/menus/header/")], []


def r_block_types(env):
    return [env.staff.get(f"{V1}/staff/block-types/")], []


def r_staff_list(kind):
    def recipe(env):
        empty = env.staff.get(f"{V1}/staff/{kind}/")
        if kind == "pages":
            _live_page(env.staff, "a")
            make_page(env.staff, "b")
            make_page(env.staff, "c", og_image="page/x")
        elif kind == "posts":
            tag = env.staff.post(f"{V1}/staff/tags/", {"locale": "en", "slug": "t", "name": "T"},
                                 format="json").json()
            _live_post(env.staff, "a", tags=[tag["id"]])
            make_post(env.staff, "b")
            transition(env.staff, "post", make_post(env.staff, "c")["id"], "scheduled", in_future())
        elif kind == "tags":
            for s in ("a", "b", "c"):
                env.staff.post(f"{V1}/staff/tags/", {"locale": "en", "slug": s, "name": s}, format="json")
        elif kind == "menus":
            _menu(env)
            env.staff.post(f"{V1}/staff/menus/", {"locale": "en", "key": "footer"}, format="json")
        elif kind == "redirects":
            for s in ("a", "b", "c"):
                env.staff.post(f"{V1}/staff/redirects/", {"locale": "en", "old_path": f"/{s}",
                                                          "new_path": "/x"}, format="json")
        return [env.staff.get(f"{V1}/staff/{kind}/", {"limit": 2})], [empty]
    return recipe


def r_create(kind):
    def recipe(env):
        c = env.staff
        if kind == "pages":
            return [c.post(f"{V1}/staff/pages/", {"locale": "en", "slug": "x", "title": "X", "blocks": [rich()]},
                           format="json")], []
        if kind == "posts":
            return [c.post(f"{V1}/staff/posts/", {"locale": "en", "slug": "x", "title": "X", "blocks": [rich()]},
                           format="json")], []
        if kind == "tags":
            return [c.post(f"{V1}/staff/tags/", {"locale": "en", "slug": "x", "name": "X"}, format="json")], []
        if kind == "menus":
            return [_menu(env)], []
        return [c.post(f"{V1}/staff/redirects/", {"locale": "en", "old_path": "/a", "new_path": "/b"},
                       format="json")], []
    return recipe


def _obj(env, kind):
    return (_live_page if kind == "pages" else _live_post)(env.staff, "obj")


def r_detail(kind):
    def recipe(env):
        obj = _obj(env, kind)
        return [env.staff.get(f"{V1}/staff/{kind}/{obj['id']}/")], []
    return recipe


def r_patch(kind):
    def recipe(env):
        obj = _obj(env, kind)
        return [env.staff.patch(f"{V1}/staff/{kind}/{obj['id']}/", {"version": obj["version"], "title": "New"},
                                format="json")], []
    return recipe


def r_action(kind, action):
    def recipe(env):
        obj = _obj(env, kind)
        base = f"{V1}/staff/{kind}/{obj['id']}"
        if action == "preview-token":
            return [env.staff.post(f"{base}/preview-token/")], []
        if action == "revisions":
            return [env.staff.get(f"{base}/revisions/")], []
        if action == "restore":
            return [env.staff.post(f"{base}/revisions/1/restore/")], []
        if action == "transition":
            return [env.staff.post(f"{base}/transition/", {"to": "scheduled",
                                                           "publish_at": in_future().isoformat()}, format="json")], []
        return [env.staff.post(f"{base}/variants/", {"locale": "de"}, format="json")], []
    return recipe


def r_menu_detail(method):
    def recipe(env):
        menu = _menu(env).json()
        url = f"{V1}/staff/menus/{menu['id']}/"
        if method == "GET":
            return [env.staff.get(url)], []
        return [env.staff.put(url, {"title": "T", "items": [{"label": "x", "target_type": "url", "url": "/x"}]},
                              format="json")], []
    return recipe


def r_tag_patch(env):
    tag = env.staff.post(f"{V1}/staff/tags/", {"locale": "en", "slug": "x", "name": "X"}, format="json").json()
    return [env.staff.patch(f"{V1}/staff/tags/{tag['id']}/", {"name": "Y"}, format="json")], []


RECIPES = {
    ("GET", V1 + "/public/resolve/", 200): r_resolve,
    ("GET", V1 + "/public/preview/", 200): r_preview,
    ("GET", V1 + "/public/posts/", 200): r_posts,
    ("GET", V1 + "/public/posts/{slug}/", 200): r_post,
    ("GET", V1 + "/public/post-archive/", 200): r_archive,
    ("GET", V1 + "/public/tags/", 200): r_tags,
    ("GET", V1 + "/public/menus/{key}/", 200): r_menu,
    ("GET", V1 + "/staff/block-types/", 200): r_block_types,
    ("GET", V1 + "/staff/menus/{menu_id}/", 200): r_menu_detail("GET"),
    ("PUT", V1 + "/staff/menus/{menu_id}/", 200): r_menu_detail("PUT"),
    ("PATCH", V1 + "/staff/tags/{tag_id}/", 200): r_tag_patch,
}
for _kind in ("pages", "posts", "tags", "menus", "redirects"):
    RECIPES[("GET", f"{V1}/staff/{_kind}/", 200)] = r_staff_list(_kind)
    RECIPES[("POST", f"{V1}/staff/{_kind}/", 201)] = r_create(_kind)
for _kind in ("pages", "posts"):
    base = f"{V1}/staff/{_kind}/{{obj_id}}/"
    RECIPES[("GET", base, 200)] = r_detail(_kind)
    RECIPES[("PATCH", base, 200)] = r_patch(_kind)
    RECIPES[("POST", base + "preview-token/", 200)] = r_action(_kind, "preview-token")
    RECIPES[("GET", base + "revisions/", 200)] = r_action(_kind, "revisions")
    RECIPES[("POST", base + "revisions/{number}/restore/", 200)] = r_action(_kind, "restore")
    RECIPES[("POST", base + "transition/", 200)] = r_action(_kind, "transition")
    RECIPES[("POST", base + "variants/", 201)] = r_action(_kind, "variants")


class Env:
    def __init__(self, anon, staff):
        self.anon, self.staff = anon, staff


def test_every_declared_operation_has_a_recipe():
    declared = {(m, p, c) for m, p, c, _ in OPERATIONS}
    assert declared == set(RECIPES), {
        "missing": sorted(declared - set(RECIPES)),
        "stale": sorted(set(RECIPES) - declared),
    }


@pytest.mark.parametrize("method,path,code,body_schema", OPERATIONS,
                         ids=[f"{m} {p} {c}" for m, p, c, _ in OPERATIONS])
def test_wire_matches_the_declared_body(method, path, code, body_schema, api_client, staff_client):
    populated, empty = RECIPES[(method, path, code)](Env(api_client, staff_client))
    validator = _validator(body_schema)
    for resp in populated + empty:
        assert resp.status_code == code, (method, path, resp.status_code, resp.content)
        errors = sorted(validator.iter_errors(resp.json()), key=str)
        assert not errors, [e.message for e in errors[:5]]
    for resp in populated:
        data = resp.json()
        for key in ("items", "months", "blocks"):
            if key in data:
                assert data[key], f"{method} {path}: populated '{key}' came back empty"
    for resp in empty:
        data = resp.json()
        for key in ("items", "months"):
            if key in data:
                assert not data[key], f"{method} {path}: the empty state is not empty"


def test_the_gate_is_not_blind(staff_client):
    """Inversion: a body validated against a wrong schema must fail."""
    page = make_page(staff_client, "x")
    body = staff_client.get(f"{V1}/staff/pages/{page['id']}/").json()
    schema = SCHEMA["paths"][V1 + "/staff/pages/{obj_id}/"]["get"]["responses"]["200"][
        "content"]["application/json"]["schema"]
    assert not list(_validator(schema).iter_errors(body))
    assert list(_validator(schema).iter_errors(dict(body, version="1")))
