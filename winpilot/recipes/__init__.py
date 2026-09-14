"""Application Recipes: Application-specific automation routines."""

from winpilot.recipes.base import BaseRecipe
from winpilot.recipes.claude_desktop import ClaudeDesktopRecipe, get_all_claude_instances

__all__ = ["BaseRecipe", "ClaudeDesktopRecipe", "get_all_claude_instances"]
