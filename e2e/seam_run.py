"""Seam run: cms with the real cdn, forms, translate and core sitemap, in one minimal host.

Usage (``make seam``): ``python seam_run.py <xsd dir>`` after ``migrate
--run-syncdb``. The xsd dir holds sitemaps.org's ``sitemap.xsd`` and
``siteindex.xsd`` next to ``xhtml-link.xsd`` / ``urlset-with-xhtml.xsd``.
Prints one line per step (step | observable) and exits non-zero on a miss.
"""
import hashlib
import json
import os
import sys
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "seamhost.settings")
import django  # noqa: E402

django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from django.test import Client  # noqa: E402
from lxml import etree  # noqa: E402

XSD = sys.argv[1]
V1 = "/cms/api/v1"
obs = []


def record(step, observable, ok):
    obs.append({"step": step, "observable": observable, "ok": bool(ok)})


def png(seed):
    import pyvips

    img = pyvips.Image.black(32, 24) + seed
    return img.write_to_buffer(".png")


from django.contrib.auth import get_user_model  # noqa: E402
from stapel_cdn.models import Image  # noqa: E402
from stapel_forms.models import Form, FormVersion  # noqa: E402
from stapel_cms.models import Page  # noqa: E402
from seamhost import mockllm  # noqa: E402

suffix = uuid.uuid4().hex[:6]
staff = get_user_model().objects.create_user(username=f"editor-{suffix}", email=f"e{suffix}@x.test",
                                             password="x", is_staff=True)
c = Client()
c.force_login(staff)

refs = []
for seed in (10, 200):
    data = png(seed)
    digest = hashlib.sha256(data + suffix.encode()).hexdigest()
    Image.objects.create(type="cms", file_hash=digest, original=ContentFile(data, name=f"{digest}.png"),
                         original_filename=f"g{seed}.png", file_extension="png", original_size=len(data))
    refs.append(f"cms/{digest}")

form = Form.objects.create(workspace_id=uuid.uuid4(), title="Contact")
form.active_version = FormVersion.objects.create(form=form, version=1, schema={"fields": []})
form.state = "open"
form.save()
draft_form = Form.objects.create(workspace_id=uuid.uuid4(), title="Later")

long_para = ("Fresh bread is baked here every single morning before sunrise. " * 120).strip()
blocks = [
    {"type": "hero", "id": "h", "data": {"heading": "Welcome", "media": refs[0]}},
    {"type": "rich_text", "id": "r", "data": {"doc": {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "We bake "},
                                          {"type": "text", "text": "bread", "marks": [{"type": "bold"}]}]},
        {"type": "paragraph", "content": [{"type": "text", "text": long_para}]}]}}},
    {"type": "gallery", "id": "g", "data": {"items": [{"media": refs[0], "alt": "Oven"},
                                                      {"media": refs[1], "alt": "Loaf", "caption": "Rye"}]}},
    {"type": "form", "id": "f", "data": {"form_id": form.public_id, "title": "Write to us"}},
]
slug = f"about-{suffix}"
resp = c.post(f"{V1}/staff/pages/", {"locale": "en", "slug": slug, "title": "About", "blocks": blocks},
              content_type="application/json")
page = resp.json()
record("create page (hero+rich text+gallery+form)", f"{resp.status_code} warnings={page.get('warnings')}",
       resp.status_code == 201 and page["warnings"] == [])

bad = c.post(f"{V1}/staff/pages/", {"locale": "en", "slug": f"x-{suffix}", "title": "X",
                                    "blocks": [{"type": "form", "id": "f", "data": {"form_id": "nope"}}]},
             content_type="application/json")
record("form block, unknown form", f"{bad.status_code} {bad.json()['localizable_error']} {bad.json()['params']}",
       bad.status_code == 400)
drafty = c.post(f"{V1}/staff/pages/", {"locale": "en", "slug": f"y-{suffix}", "title": "Y",
                                       "blocks": [{"type": "form", "id": "f",
                                                   "data": {"form_id": draft_form.public_id}}]},
                content_type="application/json")
refused = c.post(f"{V1}/staff/pages/{drafty.json()['id']}/transition/", {"to": "published"},
                 content_type="application/json")
record("form block, unpublished form", f"save {drafty.status_code} warnings={[w['code'] for w in drafty.json()['warnings']]}; "
       f"publish {refused.status_code} {refused.json()['localizable_error']}",
       drafty.status_code == 201 and refused.status_code == 409)

pub = c.post(f"{V1}/staff/pages/{page['id']}/transition/", {"to": "published"}, content_type="application/json")
record("publish en", f"{pub.status_code} status={pub.json().get('status')}", pub.status_code == 200)
row = Page.objects.get(pk=page["id"])
img_refs = {r: Image.objects.get(file_hash=r.split('/')[1]).refs for r in refs}
record("media refs sync (cdn.refs_sync)", f"Page.media_refs={row.media_refs}; cdn Image.refs={img_refs}",
       sorted(row.media_refs) == sorted(refs) and all(v == [f"cms/page/{page['id']}"] for v in img_refs.values()))

before = len(mockllm.CALLS)
var = c.post(f"{V1}/staff/pages/{page['id']}/variants/", {"locale": "de", "machine_translate": True},
             content_type="application/json")
vb = var.json()
texts = vb["blocks"][1]["data"]["doc"]["content"]
long_out = texts[1]["content"][0]["text"]
record("machine-translated variant (translate.text)",
       f"{var.status_code} title={vb.get('title')!r} hero={vb['blocks'][0]['data']['heading']!r} "
       f"nodes={[n['text'] for n in texts[0]['content']]} marks={texts[0]['content'][1].get('marks')} "
       f"long node {len(long_para)} chars -> {long_out.count('[de] ')} pieces; provider batches={mockllm.CALLS[before:]}",
       var.status_code == 201 and vb["title"] == "[de] About" and long_out.count("[de] ") >= 2)
pub_de = c.post(f"{V1}/staff/pages/{vb['id']}/transition/", {"to": "published"}, content_type="application/json")
record("publish de", f"{pub_de.status_code}", pub_de.status_code == 200)

anon = Client()
index = anon.get("/sitemap.xml")
root = etree.fromstring(index.content)
siteindex = etree.XMLSchema(etree.parse(os.path.join(XSD, "siteindex.xsd")))
record("GET /sitemap.xml (core view)", f"{index.status_code} {index['Content-Type']} xsd(siteindex)={siteindex.validate(root)}",
       index.status_code == 200 and siteindex.validate(root))
ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}
loc = root.find("sm:sitemap/sm:loc", ns).text
page1 = anon.get(loc.replace("https://seam.example", ""))
urlset = etree.fromstring(page1.content)
schema = etree.XMLSchema(etree.parse(os.path.join(XSD, "urlset-with-xhtml.xsd")))
valid = schema.validate(urlset)
mine = {u.findtext("sm:loc", namespaces=ns): {link.get("hreflang"): link.get("href") for link in u.findall("x:link", ns)}
        for u in urlset.findall("sm:url", ns) if slug in u.findtext("sm:loc", namespaces=ns)}
record("GET sitemap page: XSD (sitemap 0.9 + xhtml:link) + hreflang",
       f"{page1.status_code} xsd={valid} {'' if valid else schema.error_log} entries={json.dumps(mine)}",
       valid and len(mine) == 2 and all(set(v) == {"en", "de"} for v in mine.values()))

for o in obs:
    print(("OK  " if o["ok"] else "FAIL") + " | " + o["step"] + " | " + o["observable"][:600])
sys.exit(0 if all(o["ok"] for o in obs) else 1)
