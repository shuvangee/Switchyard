"""Routing strategies.

Starts with rule-based routing (V1) and later adds confidence/escalation
(V2) and learned routing (V3). Kept swappable behind a common interface so
strategies can be compared experimentally.
"""
