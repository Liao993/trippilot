"""Statically validate TripPilot notebook and source files.

These checks run in CI and locally without executing anything or
contacting Databricks. For .ipynb files the validator checks the
notebook JSON structure and the Python syntax of code cells, skipping
cells that begin with a notebook magic command (for example %md or
%pip), which is not standard Python. Plain .py files under notebooks/
are checked as ordinary Python source.

A file that passes is not guaranteed to run correctly at runtime; that
still requires a separate Databricks runtime check.
"""

import ast
import json
from pathlib import Path
from typing import Any

VALID_CELL_TYPES = {"code", "markdown", "raw"}
MAGIC_PREFIXES = ("%", "!")


def _source_to_text(source: Any) -> str:
    if isinstance(source, str):
        return source
    return "".join(part for part in source if isinstance(part, str))


def _starts_with_magic(source_text: str) -> bool:
    for line in source_text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.startswith(MAGIC_PREFIXES)
    return False


def validate_notebook_file(path: Path, label: str) -> list[str]:
    """Validate one .ipynb file; return errors naming the file and reason."""
    errors: list[str] = []
    try:
        with path.open("r", encoding="utf-8") as file:
            notebook = json.load(file)
    except json.JSONDecodeError as exc:
        return [f"{label}: invalid notebook JSON: {exc}"]
    except OSError as exc:
        return [f"{label}: cannot read file: {exc}"]

    if not isinstance(notebook, dict):
        return [f"{label}: notebook must be a JSON mapping"]

    nbformat = notebook.get("nbformat")
    if not isinstance(nbformat, int) or nbformat < 4:
        errors.append(f"{label}: 'nbformat' must be an integer >= 4, got {nbformat!r}")

    cells = notebook.get("cells")
    if not isinstance(cells, list) or len(cells) == 0:
        errors.append(f"{label}: 'cells' must be a non-empty list")
        return errors

    for index, cell in enumerate(cells):
        cell_label = f"{label}: cell {index}"
        if not isinstance(cell, dict):
            errors.append(f"{cell_label} must be a mapping")
            continue

        cell_type = cell.get("cell_type")
        if cell_type not in VALID_CELL_TYPES:
            errors.append(f"{cell_label}: invalid 'cell_type' {cell_type!r}")

        source = cell.get("source")
        is_valid_source = isinstance(source, str) or (
            isinstance(source, list) and all(isinstance(part, str) for part in source)
        )
        if not is_valid_source:
            errors.append(f"{cell_label}: 'source' must be a string or list of strings")
            continue

        if cell_type == "code":
            source_text = _source_to_text(source)
            if _starts_with_magic(source_text):
                continue
            try:
                ast.parse(source_text)
            except (SyntaxError, ValueError) as exc:
                errors.append(f"{cell_label} (code): invalid Python: {exc}")

    return errors


def validate_python_file(path: Path, label: str) -> list[str]:
    """Validate one plain .py source file; return errors naming the file."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{label}: cannot read file: {exc}"]

    try:
        ast.parse(source)
    except (SyntaxError, ValueError) as exc:
        return [f"{label}: invalid Python: {exc}"]

    return []


def validate_notebook_sources(repo_root: str | Path | None = None) -> list[str]:
    """Validate every .ipynb and .py file under notebooks/.

    Returns a list of error messages naming each file and the reason;
    an empty list means every file is valid.
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    notebooks_dir = root / "notebooks"

    if not notebooks_dir.is_dir():
        return [f"notebooks/: directory not found under {root}"]

    files = sorted(
        path for path in notebooks_dir.rglob("*") if path.suffix in {".ipynb", ".py"}
    )
    if not files:
        return [f"notebooks/: no .ipynb or .py files found under {notebooks_dir}"]

    errors: list[str] = []
    for path in files:
        label = path.relative_to(root).as_posix()
        if path.suffix == ".ipynb":
            errors.extend(validate_notebook_file(path, label))
        else:
            errors.extend(validate_python_file(path, label))

    return errors


def main() -> None:
    """Validate notebooks/ from the repository root; exit non-zero on failure."""
    errors = validate_notebook_sources()
    if errors:
        raise SystemExit("Notebook/source validation failed:\n- " + "\n- ".join(errors))
    print("All notebook and source files under notebooks/ are valid.")


if __name__ == "__main__":
    main()
