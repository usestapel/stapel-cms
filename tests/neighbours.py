"""Rows in real neighbour modules, made the way their own services leave them."""
from __future__ import annotations

import uuid


def make_form(*, published: bool, title: str = "Contact") -> str:
    """A stapel-forms form; ``published`` = open with an active version. Returns its public_id."""
    from stapel_forms.models import Form, FormVersion

    form = Form.objects.create(workspace_id=uuid.uuid4(), title=title)
    if published:
        version = FormVersion.objects.create(form=form, version=1, schema={"fields": []})
        form.active_version = version
        form.state = "open"
        form.save()
    return form.public_id


def delete_form(public_id: str) -> None:
    from django.utils import timezone
    from stapel_forms.models import Form

    Form.objects.filter(public_id=public_id).update(deleted_at=timezone.now())
