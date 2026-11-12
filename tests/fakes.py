"""In-process fakes for the Functions cms calls by name."""
from __future__ import annotations


class FakeFunction:
    """Registers a callable under a comm Function name; records calls."""

    def __init__(self, name, answer=None):
        self.name = name
        self.answer = answer
        self.calls: list[dict] = []

    def __call__(self, payload):
        self.calls.append(payload)
        if callable(self.answer):
            return self.answer(payload)
        return self.answer

    def install(self):
        from stapel_core.comm.registry import function_registry

        function_registry.register(self.name, self)
        return self

    def uninstall(self):
        from stapel_core.comm.registry import function_registry

        with function_registry._lock:
            function_registry._providers.pop(self.name, None)
            function_registry._schemas.pop(self.name, None)
