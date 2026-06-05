"""vibecodekit_mql5 — Plan v5 command modules.

Each submodule exposes a `main()` entrypoint registered as a console_script
in pyproject.toml. Per docs/anti-patterns-AVOID.md: NO master `/mql5`
router, NO query_loop, NO intent_router. Users invoke commands directly:

    mql5-build <preset> --name X --symbol Y --tf Z
    mql5-lint  <ea.mq5>
    mql5-compile <ea.mq5>
    mql5-pip-normalize <ea.mq5>
"""

__version__ = "1.6.1"
