"""stapel-cms capabilities.json emitter — thin shim over stapel_tools.capabilities."""
from pathlib import Path

from stapel_tools.capabilities import axis_group_rules, run_capabilities_cli


def main(argv=None):
    from stapel_cms._codegen import _configure

    _configure()
    from stapel_cms.conf import DEFAULTS
    from stapel_cms.urls import GATE_REGISTRY

    # CTO-facing axes: BLOG_ENABLED (unmounts the blog routes), STAFF_AUTHZ
    # (who may edit) and EMBED_HOSTS (which embeds render; published to
    # clients in the resolve answer's meta). BLOCK_TYPES is the extension seam.
    axes = {"BLOG_ENABLED", "STAFF_AUTHZ", "EMBED_HOSTS"}
    return run_capabilities_cli(
        argv,
        repo=Path(__file__).resolve().parent,
        canonical_prefix="/cms/api/v1",
        defaults=DEFAULTS,
        registry=GATE_REGISTRY,
        is_axis=lambda k: k in axes,
        axis_group=axis_group_rules(exact={"BLOG_ENABLED": "cms.blog", "STAFF_AUTHZ": "cms.staff",
                                           "EMBED_HOSTS": "cms.embed"}),
        prog="stapel-cms-capabilities",
    )


if __name__ == "__main__":
    raise SystemExit(main())
