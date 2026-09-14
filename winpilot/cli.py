"""
WinPilot Command Line Interface (CLI): Human-facing terminal controls with Rich formatting.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import sys

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.tree import Tree
import typer

from winpilot.compose.query import Query
from winpilot.core.input import Input
from winpilot.core.screen import Screen
from winpilot.core.uia import UIATree
from winpilot.core.window import Window, find_window, list_windows
from winpilot.recipes.claude_desktop import ClaudeDesktopRecipe

app = typer.Typer(
    name="winpilot",
    help="Windows Desktop Automation Toolkit for AI Agents & Humans.",
    add_completion=False,
)
recipe_app = typer.Typer(help="Application automation recipes.")
app.add_typer(recipe_app, name="recipe")

console = Console(force_terminal=True, legacy_windows=False)


def _resolve_window(hwnd_or_title: str) -> Window:
    if hwnd_or_title.isdigit():
        w = Window(int(hwnd_or_title))
    else:
        w = find_window(title_regex=hwnd_or_title)
    if not w or not w.is_valid:
        console.print(f"[bold red]Error:[/] Window matching '{hwnd_or_title}' not found.")
        raise typer.Exit(code=1)
    return w


@app.command("list")
@app.command("list-windows")
def list_cmd(
    filter: Optional[str] = typer.Option(None, "--filter", "-f", help="Regex filter for window title"),
    process: Optional[str] = typer.Option(None, "--process", "-p", help="Filter by process name (e.g. claude.exe)"),
    all: bool = typer.Option(False, "--all", "-a", help="Include invisible windows"),
):
    """List open Windows top-level windows."""
    wins = list_windows(title_regex=filter, process_name=process, visible_only=not all)

    table = Table(title="Windows Desktop Windows", show_lines=True)
    table.add_column("HWND", style="cyan", justify="right")
    table.add_column("PID", style="dim", justify="right")
    table.add_column("Process", style="green")
    table.add_column("Title", style="bold white")
    table.add_column("State", style="magenta")
    table.add_column("Bounds (L,T,R,B)", style="dim")

    for w in wins:
        state = "Visible"
        if w.is_cloaked:
            state = "Cloaked (Desktop 2+)"
        elif w.is_minimized:
            state = "Minimized"

        r = w.rect
        table.add_row(
            str(w.hwnd),
            str(w.pid),
            w.process_name,
            w.title[:45] + ("..." if len(w.title) > 45 else ""),
            state,
            f"{r[0]},{r[1]},{r[2]},{r[3]}",
        )

    console.print(table)


@app.command("focus")
def focus_cmd(window: str = typer.Argument(..., help="Window title or HWND")):
    """Bring a window to foreground (uncloaks virtual desktops & breaks focus locks)."""
    w = _resolve_window(window)
    ok = w.focus()
    if ok:
        console.print(f"[bold green]✓[/] Focused '[bold white]{w.title}[/]' (HWND={w.hwnd})")
    else:
        console.print(f"[bold red]✗[/] Failed to focus '[bold white]{w.title}[/]' (HWND={w.hwnd})")


@app.command("inspect")
def inspect_cmd(
    window: str = typer.Argument(..., help="Window title or HWND"),
    depth: int = typer.Option(3, "--depth", "-d", help="Max traversal depth in UIA tree"),
    json_out: bool = typer.Option(False, "--json", help="Output as raw JSON"),
):
    """Dump and visually render the UI Automation accessibility tree."""
    w = _resolve_window(window)
    tree_builder = UIATree(w)
    raw_data = tree_builder.dump_tree(max_depth=depth, visible_only=True)

    if json_out:
        console.print(json.dumps(raw_data, indent=2))
        return

    def _build_rich_tree(data: dict, parent_tree: Tree):
        name_str = f" [bold white]\"{data.get('name')}\"[/]" if data.get("name") else ""
        id_str = f" [dim]id={data.get('id')}[/]" if data.get("id") else ""
        type_str = f"[cyan]{data.get('type')}[/]"
        node = parent_tree.add(f"{type_str}{name_str}{id_str}")
        for child in data.get("children", []):
            _build_rich_tree(child, node)

    root_tree = Tree(f"[bold green]Window: {w.title}[/] (HWND={w.hwnd}, PID={w.pid})")
    for c in raw_data.get("children", []):
        _build_rich_tree(c, root_tree)

    console.print(root_tree)


@app.command("click")
def click_cmd(
    window: str = typer.Argument(..., help="Window title or HWND"),
    query: str = typer.Argument(..., help="Selector query (e.g. Button[Name*='Model'])"),
):
    """Click a UI element inside a window by selector query."""
    w = _resolve_window(window)
    w.focus()
    tree = UIATree(w)
    elem = Query.find_one(tree, query)
    if not elem:
        console.print(f"[bold red]Error:[/] Element matching query {query!r} not found.")
        raise typer.Exit(code=1)

    ok = elem.click(method="auto")
    console.print(f"[bold green]✓[/] Clicked element [cyan]{elem.name}[/] ({elem.control_type}): {ok}")


@app.command("paste")
def paste_cmd(
    window: str = typer.Argument(..., help="Window title or HWND"),
    text: str = typer.Argument(..., help="Text to paste"),
    submit: bool = typer.Option(False, "--submit", "-s", help="Press Enter after pasting"),
):
    """Paste text into a window via clipboard."""
    w = _resolve_window(window)
    w.focus()
    ok = Input.paste_text(text, submit_enter=submit)
    console.print(f"[bold green]✓[/] Pasted into [white]{w.title}[/]: {ok}")


@app.command("screenshot")
def screenshot_cmd(
    window: Optional[str] = typer.Option(None, "--window", "-w", help="Window title or HWND (defaults to full screen)"),
    output: Path = typer.Option(Path("screenshot.png"), "--output", "-o", help="Output PNG path"),
):
    """Capture a screenshot of a window or desktop."""
    if window:
        w = _resolve_window(window)
        img = Screen.capture_window(w)
    else:
        img = Screen.capture_desktop()

    if not img:
        console.print("[bold red]Error:[/] Failed to capture screenshot.")
        raise typer.Exit(code=1)

    saved_path = Screen.save(img, output)
    console.print(f"[bold green]✓[/] Screenshot saved to: [cyan]{saved_path}[/]")


@app.command("serve")
def serve_cmd(
    transport: str = typer.Option("stdio", "--transport", "-t", help="MCP transport: stdio or sse"),
    port: int = typer.Option(8100, "--port", "-p", help="Port for SSE transport"),
):
    """Launch the WinPilot MCP Server for AI coding agents."""
    from winpilot.mcp_server import mcp

    console.print(f"[bold green]⚡ Starting WinPilot MCP Server ({transport})...[/]")
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="sse")


# Recipe Subcommands
@recipe_app.command("claude-model")
def recipe_claude_model(
    model: str = typer.Option("haiku", "--model", "-m", help="Target model: haiku, sonnet, opus"),
    target: str = typer.Option("Claude", "--target", "-t", help="Target window title or HWND"),
):
    """Set the active model in Claude Desktop via UIA automation."""
    recipe = ClaudeDesktopRecipe(target)
    console.print(f"[*] Selecting model '[bold cyan]{model}[/]' in Claude Desktop...")
    res = recipe.set_model(model)
    if res.get("success"):
        console.print(f"[bold green]✓ {res.get('message')}[/]")
    else:
        console.print(f"[bold red]✗ {res.get('error')}[/]")


@recipe_app.command("claude-prompt")
def recipe_claude_prompt(
    prompt: str = typer.Argument(..., help="Prompt text to send"),
    target: str = typer.Option("Claude", "--target", "-t", help="Target window title or HWND"),
    no_submit: bool = typer.Option(False, "--no-submit", help="Do not press enter"),
):
    """Send prompt to Claude Desktop."""
    recipe = ClaudeDesktopRecipe(target)
    ok = recipe.send_prompt(prompt, submit=not no_submit)
    console.print(f"[bold green]✓ Prompt dispatched to Claude: {ok}[/]")


if __name__ == "__main__":
    app()
