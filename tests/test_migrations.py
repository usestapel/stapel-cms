"""Migrations from zero, and no model change without a migration."""
from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_no_missing_migrations():
    out = StringIO()
    call_command("makemigrations", "cms", "--check", "--dry-run", stdout=out)


@pytest.mark.django_db(transaction=True)
def test_migrate_from_zero_and_back():
    call_command("migrate", "cms", "zero", verbosity=0)
    call_command("migrate", "cms", verbosity=0)
