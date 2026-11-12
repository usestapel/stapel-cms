"""Create the usual pages (about, contacts, terms, privacy, FAQ) as drafts."""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create about/contacts/terms/privacy/faq pages as drafts (idempotent; never publishes)."

    def add_arguments(self, parser):
        parser.add_argument("--site", default=None, help="Site key (default: the primary site, '' single-host).")
        parser.add_argument("--locale", default=None, help="Locale (default: DEFAULT_LOCALE).")

    def handle(self, *args, **options):
        from stapel_cms import sitekeys
        from stapel_cms.services import CmsError
        from stapel_cms.services.seed import seed

        site = options["site"] if options["site"] is not None else sitekeys.default_key()
        try:
            created = seed(site=site, locale=options["locale"])
        except CmsError as exc:
            raise CommandError(f"{exc.key} {exc.params}") from None
        if created:
            self.stdout.write("created drafts: " + ", ".join(created))
        else:
            self.stdout.write("nothing to create: every seed page exists")
