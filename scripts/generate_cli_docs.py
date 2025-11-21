#!/usr/bin/env python3
"""Generate CLI documentation from Click CLI and embed it in README.md."""

import re
import sys
from pathlib import Path

from click.testing import CliRunner

from pkm_tool.cli import main


def extract_help_text() -> str:
    """Extract help text from CLI using Click's CliRunner."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    if result.exit_code != 0:
        print(f"Error: CLI invocation failed with exit code {result.exit_code}", file=sys.stderr)
        print(result.output, file=sys.stderr)
        sys.exit(1)

    return result.output


def format_help_as_markdown(help_text: str) -> str:
    """
    Format Click help text as Markdown.

    Extracts command description and options from the help text.
    """
    lines = help_text.strip().split("\n")

    markdown_lines = []
    markdown_lines.append("```bash")
    markdown_lines.append("pkm --help")
    markdown_lines.append("```")
    markdown_lines.append("")
    markdown_lines.append("```")
    markdown_lines.extend(lines)
    markdown_lines.append("```")
    markdown_lines.append("")

    # Extract options for a more structured display
    in_options = False
    options = []
    current_option = None

    for line in lines:
        if line.strip().startswith("Options:"):
            in_options = True
            continue

        if in_options:
            if not line.strip():
                continue
            # Options start with "  -" (2 spaces and a dash)
            if line.startswith("  -"):
                # Save previous option if exists
                if current_option:
                    options.append(current_option)
                # Start new option
                current_option = line.strip()
            elif current_option and line.startswith("                                "):
                # Continuation line (many spaces)
                current_option += " " + line.strip()

    # Don't forget the last option
    if current_option:
        options.append(current_option)

    if options:
        markdown_lines.append("### Available Options")
        markdown_lines.append("")
        for opt in options:
            # Parse option line (e.g., "-d, --date TEXT  Date to fetch data for...")
            # Split on multiple spaces (2 or more) to separate option from description
            parts = re.split(r'\s{2,}', opt, maxsplit=1)
            if len(parts) >= 2:
                opt_name = parts[0].strip()
                opt_desc = parts[1].strip()
                markdown_lines.append(f"- **`{opt_name}`**: {opt_desc}")
            else:
                # Fallback for options without description
                markdown_lines.append(f"- **`{opt.strip()}`**")
        markdown_lines.append("")

    return "\n".join(markdown_lines)


def update_readme(readme_path: Path, generated_docs: str) -> bool:
    """
    Update README.md with generated documentation between markers.

    Args:
        readme_path: Path to README.md file
        generated_docs: Generated documentation to insert

    Returns:
        True if successful, False otherwise
    """
    if not readme_path.exists():
        print(f"Error: {readme_path} not found", file=sys.stderr)
        return False

    content = readme_path.read_text()

    # Find markers
    start_marker = "<!-- CLI_USAGE_START -->"
    end_marker = "<!-- CLI_USAGE_END -->"

    if start_marker not in content or end_marker not in content:
        print(f"Error: Markers not found in {readme_path}", file=sys.stderr)
        print(f"Please add '{start_marker}' and '{end_marker}' markers", file=sys.stderr)
        return False

    # Replace content between markers
    pattern = re.compile(
        rf"({re.escape(start_marker)})(.*?)({re.escape(end_marker)})",
        re.DOTALL
    )

    new_content = pattern.sub(
        rf"\1\n\n{generated_docs}\n{end_marker}",
        content
    )

    # Write back to file
    readme_path.write_text(new_content)
    return True


def main_script() -> int:
    """Main script entry point."""
    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    readme_path = project_root / "README.md"

    print(f"Extracting CLI help text...")
    help_text = extract_help_text()

    print(f"Formatting as Markdown...")
    generated_docs = format_help_as_markdown(help_text)

    print(f"Updating {readme_path}...")
    if update_readme(readme_path, generated_docs):
        print("✓ README.md successfully updated")
        return 0
    else:
        print("✗ Failed to update README.md", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main_script())
