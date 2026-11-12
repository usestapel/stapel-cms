# stapel-cms — contract emission + drift gate.
#
# Emits the contract triad (schema.json + flows.json + errors.json),
# capabilities.json, llms.txt and README.md from a single-module
# {reservations + core} instance mounted at /reservations/api/v1/. The authoritative CI
# gate is tests/test_contract.py; these targets are the dev loop.
# Edit docs/readme.md, never README.md.
PYTHON ?= python3
LLMS_BUDGET ?= 6000

.PHONY: contract contract-check migration-lint seam

# Seam run with the real neighbours installed (stapel-cdn[images], stapel-forms,
# stapel-translate, a core with stapel_core.django.sitemap, lxml): boots
# e2e/seamhost on a throwaway database, then publishes, translates and
# validates sitemap.xml against the sitemaps.org XSD. macOS strips DYLD_* from
# make and sh: pass the libvips directory as LIBVIPS_DIR=/opt/homebrew/lib.
SEAM_PYTHON = $(abspath $(shell command -v $(PYTHON)))
SEAM_RUN = DYLD_FALLBACK_LIBRARY_PATH="$(LIBVIPS_DIR)" $(SEAM_PYTHON)
SEAM_DIR = $(CURDIR)/e2e
seam:
	@tmp=$$(mktemp -d); mkdir -p e2e/.xsd; \
	cp e2e/xhtml-link.xsd e2e/urlset-with-xhtml.xsd e2e/.xsd/; \
	for f in sitemap.xsd siteindex.xsd; do \
		[ -s e2e/.xsd/$$f ] || curl -fsS -m 30 -o e2e/.xsd/$$f https://www.sitemaps.org/schemas/sitemap/0.9/$$f || exit 1; \
	done; \
	cd "$$tmp" && $(SEAM_RUN) $(SEAM_DIR)/manage.py migrate --run-syncdb -v0 && \
	$(SEAM_RUN) $(SEAM_DIR)/manage.py check --fail-level ERROR >/dev/null 2>&1 && \
	$(SEAM_RUN) $(SEAM_DIR)/seam_run.py $(SEAM_DIR)/.xsd

contract:
	$(PYTHON) -m stapel_cms._codegen --out docs
	$(PYTHON) -m stapel_cms._capabilities --out docs
	$(PYTHON) -m stapel_tools.llms_txt . --out docs --budget $(LLMS_BUDGET)
	$(PYTHON) -m stapel_tools.readme .

contract-check:
	@tmp=$$(mktemp -d); \
	$(PYTHON) -m stapel_cms._codegen --out "$$tmp" || { rm -rf "$$tmp"; exit 1; }; \
	$(PYTHON) -m stapel_cms._capabilities --out "$$tmp" || { rm -rf "$$tmp"; exit 1; }; \
	$(PYTHON) -m stapel_tools.llms_txt . --out "$$tmp" --budget $(LLMS_BUDGET) || { rm -rf "$$tmp"; exit 1; }; \
	rc=0; \
	for f in schema.json flows.json errors.json capabilities.json llms.txt; do \
		if ! diff -q "docs/$$f" "$$tmp/$$f" >/dev/null 2>&1; then \
			echo "DRIFT: docs/$$f is stale — run 'make contract' and commit it"; \
			diff "docs/$$f" "$$tmp/$$f" | head -20; rc=1; \
		fi; \
	done; \
	rm -rf "$$tmp"; \
	$(PYTHON) -m stapel_tools.readme . --check || rc=1; \
	if [ $$rc -eq 0 ]; then echo "contract-check: docs + README.md up to date"; fi; \
	exit $$rc

migration-lint:
	$(PYTHON) -m stapel_tools.migration_lint . --strict
