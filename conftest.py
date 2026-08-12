"""Root conftest.

Presence at the repo root puts the repo root on ``sys.path`` for test collection,
so ``import scenarios`` resolves (``ehm`` is installed editable by ``uv sync``).
"""
