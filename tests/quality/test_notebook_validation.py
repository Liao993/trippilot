"""Tests for static notebook and source-file validation.

Uses synthetic .ipynb/.py samples written to pytest's tmp_path, plus
one run against the repository's real notebooks. Nothing is executed;
the checks are purely structural and syntactic.
"""

import json
import sys
from pathlib import Path

start = Path.cwd().resolve()
ROOT = next(
    (
        p
        for p in [start, *start.parents]
        if (p / "src").is_dir() and (p / "config/project.yml").is_file()
    ),
    None,
)
if ROOT is None:
    raise RuntimeError(
        "Cannot locate repository root. Open this notebook inside the Databricks Git folder."
    )
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print("Repository root:", ROOT)

from src.quality.notebook_validation import (
    validate_notebook_file,
    validate_notebook_sources,
    validate_python_file,
)


def _write_notebook(directory, name, cells, nbformat=4):
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"cells": cells, "nbformat": nbformat, "nbformat_minor": 0}),
        encoding="utf-8",
    )
    return path


def _code_cell(source):
    return {"cell_type": "code", "metadata": {}, "outputs": [], "source": source}


def _markdown_cell(source):
    return {"cell_type": "markdown", "metadata": {}, "source": source}


def test_valid_notebook_passes(tmp_path):
    path = _write_notebook(
        tmp_path,
        "notebooks/valid.ipynb",
        [
            _code_cell("x = 1\nprint(x)"),
            _markdown_cell("# Heading\nSome text."),
            _code_cell(""),
        ],
    )

    errors = validate_notebook_file(path, "notebooks/valid.ipynb")

    assert errors == []


def test_magic_cell_is_skipped_not_parsed(tmp_path):
    path = _write_notebook(
        tmp_path,
        "notebooks/magic.ipynb",
        [
            _code_cell("%md\nThis is **markdown**, not python"),
            _code_cell("%pip install ruff"),
        ],
    )

    errors = validate_notebook_file(path, "notebooks/magic.ipynb")

    assert errors == []


def test_invalid_json_reports_file(tmp_path):
    path = tmp_path / "notebooks/broken.ipynb"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json at all", encoding="utf-8")

    errors = validate_notebook_file(path, "notebooks/broken.ipynb")

    assert len(errors) == 1
    assert "notebooks/broken.ipynb" in errors[0]
    assert "invalid notebook JSON" in errors[0]


def test_missing_nbformat_and_empty_cells_are_reported(tmp_path):
    path = tmp_path / "notebooks/nofmt.ipynb"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"cells": []}), encoding="utf-8")

    errors = validate_notebook_file(path, "notebooks/nofmt.ipynb")

    assert any("'nbformat'" in error for error in errors)
    assert any("'cells'" in error for error in errors)


def test_invalid_cell_type_is_reported(tmp_path):
    path = _write_notebook(
        tmp_path,
        "notebooks/badtype.ipynb",
        [{"cell_type": "weird", "source": "text"}],
    )

    errors = validate_notebook_file(path, "notebooks/badtype.ipynb")

    assert any("invalid 'cell_type'" in error for error in errors)


def test_invalid_source_type_is_reported(tmp_path):
    path = _write_notebook(
        tmp_path,
        "notebooks/badsource.ipynb",
        [{"cell_type": "code", "source": 42}],
    )

    errors = validate_notebook_file(path, "notebooks/badsource.ipynb")

    assert any(
        "'source' must be a string or list of strings" in error for error in errors
    )


def test_code_syntax_error_reports_file_and_cell(tmp_path):
    path = _write_notebook(
        tmp_path,
        "notebooks/badcode.ipynb",
        [
            _code_cell("x = 1"),
            _code_cell("def broken(:\n    pass"),
        ],
    )

    errors = validate_notebook_file(path, "notebooks/badcode.ipynb")

    assert len(errors) == 1
    assert "notebooks/badcode.ipynb" in errors[0]
    assert "cell 1" in errors[0]
    assert "invalid Python" in errors[0]


def test_list_source_notebook_passes(tmp_path):
    path = _write_notebook(
        tmp_path,
        "notebooks/listsrc.ipynb",
        [_code_cell(["x = 1\n", "print(x)\n"])],
    )

    assert validate_notebook_file(path, "notebooks/listsrc.ipynb") == []


def test_valid_python_file_passes(tmp_path):
    path = tmp_path / "notebooks" / "ok.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("print('hello')\n", encoding="utf-8")

    assert validate_python_file(path, "notebooks/ok.py") == []


def test_empty_python_placeholder_file_passes(tmp_path):
    path = tmp_path / "notebooks" / "placeholder.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")

    assert validate_python_file(path, "notebooks/placeholder.py") == []


def test_python_syntax_error_reports_file(tmp_path):
    path = tmp_path / "notebooks" / "bad.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("def broken(:\n", encoding="utf-8")

    errors = validate_python_file(path, "notebooks/bad.py")

    assert len(errors) == 1
    assert "notebooks/bad.py" in errors[0]
    assert "invalid Python" in errors[0]


def test_real_repo_notebooks_are_valid():
    assert validate_notebook_sources(ROOT) == []


def test_missing_notebooks_directory_is_reported(tmp_path):
    errors = validate_notebook_sources(tmp_path)

    assert len(errors) == 1
    assert "notebooks/" in errors[0]
