"""
Query DSL: CSS-like selector parser and evaluator for Windows UI Automation trees.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from winpilot.core.uia import UIATree, UIElement


@dataclass
class Selector:
    control_type: str | None = None
    automation_id: str | None = None
    name_op: str | None = None  # "=", "*=", "^=", "$="
    name_val: str | None = None
    name_case_insensitive: bool = True
    class_name: str | None = None

    def matches(self, elem: UIElement) -> bool:
        # 1. Control type match
        if self.control_type and self.control_type != "*":
            if self.control_type.lower() != elem.control_type.lower():
                return False

        # 2. Automation ID match
        if self.automation_id:
            if self.automation_id.lower() != elem.automation_id.lower():
                return False

        # 3. Class name match
        if self.class_name:
            if self.class_name.lower() != elem.class_name.lower():
                return False

        # 4. Name attribute match
        if self.name_val is not None:
            actual = elem.name
            target = self.name_val
            if self.name_case_insensitive:
                actual = actual.lower()
                target = target.lower()

            if self.name_op == "=":
                if actual != target:
                    return False
            elif self.name_op == "*=":
                if target not in actual:
                    return False
            elif self.name_op == "^=":
                if not actual.startswith(target):
                    return False
            elif self.name_op == "$=":
                if not actual.endswith(target):
                    return False

        return True


def parse_query(query_str: str) -> list[Selector]:
    """
    Parses selector strings like:
      - 'Button[Name="Sonnet 5"]'
      - 'MenuItem[Name*="haiku" i]'
      - 'Edit#input_box'
      - '.menu-item'
    """
    selectors: list[Selector] = []
    # Split on hierarchy or combinators (for MVP we support simple selectors and comma lists)
    raw_selectors = [s.strip() for s in query_str.split(",") if s.strip()]

    attr_re = re.compile(r'\[\s*([a-zA-Z_]+)\s*([\*\^\$]?=)\s*["\'](.*?)["\']\s*(i)?\s*\]')
    id_re = re.compile(r'#([a-zA-Z0-9_\-]+)')
    class_re = re.compile(r'\.([a-zA-Z0-9_\-]+)')
    type_re = re.compile(r'^([a-zA-Z0-9_\*]+)')

    for s_text in raw_selectors:
        sel = Selector()

        # Extract attributes [Attr=Val]
        for m in attr_re.finditer(s_text):
            attr, op, val, flag = m.groups()
            attr_l = attr.lower()
            if attr_l in ("name", "text", "label"):
                sel.name_op = op
                sel.name_val = val
                sel.name_case_insensitive = bool(flag) or True
            elif attr_l in ("id", "automationid", "automation_id"):
                sel.automation_id = val
            elif attr_l in ("class", "classname", "class_name"):
                sel.class_name = val

        cleaned = attr_re.sub("", s_text)

        # Extract ID (#foo)
        id_m = id_re.search(cleaned)
        if id_m:
            sel.automation_id = id_m.group(1)
            cleaned = id_re.sub("", cleaned)

        # Extract Class (.bar)
        class_m = class_re.search(cleaned)
        if class_m:
            sel.class_name = class_m.group(1)
            cleaned = class_re.sub("", cleaned)

        # Extract Type (Button, MenuItem, etc.)
        type_m = type_re.search(cleaned.strip())
        if type_m:
            sel.control_type = type_m.group(1)

        selectors.append(sel)

    return selectors


class Query:
    """Evaluates a query string against a UIATree or UIElement."""

    @staticmethod
    def find_all(root_or_tree: UIATree | UIElement, query_str: str, max_depth: int = 8) -> list[UIElement]:
        selectors = parse_query(query_str)
        if not selectors:
            return []

        if isinstance(root_or_tree, UIATree):
            candidates = root_or_tree.root_element.descendants(depth=max_depth)
        else:
            candidates = root_or_tree.descendants(depth=max_depth)

        matches: list[UIElement] = []
        for elem in candidates:
            # Matches if any selector in the OR-list matches
            if any(sel.matches(elem) for sel in selectors):
                matches.append(elem)

        return matches

    @staticmethod
    def find_one(root_or_tree: UIATree | UIElement, query_str: str, max_depth: int = 8) -> UIElement | None:
        results = Query.find_all(root_or_tree, query_str, max_depth=max_depth)
        return results[0] if results else None
