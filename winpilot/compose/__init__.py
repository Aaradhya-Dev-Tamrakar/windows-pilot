"""Composition Layer: Query DSL, Wait Conditions, and Action Chains."""

from winpilot.compose.actions import ActionChain
from winpilot.compose.query import Query, parse_query
from winpilot.compose.wait import wait_for_element, wait_for_window, wait_until_gone

__all__ = [
    "Query",
    "parse_query",
    "wait_for_element",
    "wait_for_window",
    "wait_until_gone",
    "ActionChain",
]
