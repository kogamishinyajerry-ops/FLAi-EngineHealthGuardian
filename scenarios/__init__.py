"""Scenario package — vertical slices that consume the ``ehm`` platform.

Each scenario is a self-contained end-to-end use case (synthetic data → pipeline
→ Evidence → agent → audit). Scenario code must not leak into the ``ehm`` library
package; it is a consumer of the platform, not part of it.
"""
