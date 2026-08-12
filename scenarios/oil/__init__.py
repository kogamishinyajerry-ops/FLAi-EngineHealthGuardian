"""Oil vertical slice — third PHM scenario (consumption-rate / leak detection).

Stress-tests the boundary a third time with a *different* feature shape: oil
consumption is a rate derived from tank-level deltas (not a residual vs a physics
baseline), so it doesn't fit the per-snapshot ``PeerGroup`` — the scenario brings
its own fleet-rate comparison. See ADR-0011.
"""
