"""Tests for WinPilot Selector parser and Query DSL."""

from unittest.mock import MagicMock
from winpilot.compose.query import Query, parse_query, Selector


def test_parse_simple_selector():
    selectors = parse_query('Button[Name="Submit"]')
    assert len(selectors) == 1
    s = selectors[0]
    assert s.control_type == "Button"
    assert s.name_op == "="
    assert s.name_val == "Submit"


def test_parse_attributes():
    selectors = parse_query('MenuItem[Name*="haiku" i]#item-1.menu-btn')
    assert len(selectors) == 1
    s = selectors[0]
    assert s.control_type == "MenuItem"
    assert s.name_op == "*="
    assert s.name_val == "haiku"
    assert s.automation_id == "item-1"
    assert s.class_name == "menu-btn"


def test_selector_matching():
    s = Selector(control_type="Button", name_op="*=", name_val="Sonnet")

    mock_elem_match = MagicMock()
    mock_elem_match.control_type = "Button"
    mock_elem_match.name = "Claude 3.7 Sonnet"
    mock_elem_match.automation_id = "btn-1"
    mock_elem_match.class_name = "btn"
    assert s.matches(mock_elem_match) is True

    mock_elem_mismatch = MagicMock()
    mock_elem_mismatch.control_type = "Button"
    mock_elem_mismatch.name = "Haiku 4.5"
    mock_elem_mismatch.automation_id = "btn-2"
    mock_elem_mismatch.class_name = "btn"
    assert s.matches(mock_elem_mismatch) is False
