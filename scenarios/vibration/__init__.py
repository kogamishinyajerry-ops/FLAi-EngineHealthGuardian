"""Vibration vertical slice — second PHM scenario.

Built entirely in ``scenarios/`` to stress-test the "add a scenario without
touching the library" boundary (see ADR-0007). Reuses generic library primitives
(``PeerGroup``, ``residual_trend``, ``uncertainty``, ``policy``, ``Evidence``,
``run_agent``, ``AuditLog``) and brings only its own feature engineering.
"""
