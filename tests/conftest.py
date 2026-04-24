import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

import pytest
from py_app_dev.core.find import find_elements_of_type

T = TypeVar("T")


def _assert_elements(elements: list[Any], element_type: type[T], expected_count: int, filter_fn: Optional[Callable[[T], bool]] = None) -> list[T]:
    """Helper method to assert and return elements based on type and optional filter."""
    found_elements = find_elements_of_type(elements, element_type)

    if expected_count != 0:
        assert found_elements, f"No element of type {element_type.__name__} found"

    filtered_elements = found_elements
    if filter_fn:
        filtered_elements = [elem for elem in found_elements if filter_fn(elem)]

    assert len(filtered_elements) == expected_count, f"Expected {expected_count} elements of type {element_type.__name__} that met the criteria, but found {len(filtered_elements)}"

    return filtered_elements


def assert_element_of_type(elements: list[Any], element_type: type[T], filter_fn: Optional[Callable[[T], bool]] = None) -> T:
    """Assert that exactly one element of the given type exists, optionally needs to meet filter condition."""
    return _assert_elements(elements, element_type, 1, filter_fn)[0]


def assert_elements_of_type(elements: list[Any], element_type: type[T], count: int, filter_fn: Optional[Callable[[T], bool]] = None) -> list[T]:
    """Assert that exactly `count` elements of the given type exist, optionally needs to meet filter condition."""
    return _assert_elements(elements, element_type, count, filter_fn)


def get_test_data_dir() -> Path:
    """Get the path to the test data directory."""
    current_dir = Path(__file__).parent
    return current_dir / "data"


def get_test_data_file(filename: str | Path) -> Path:
    """Get the path to a specific test data file."""
    return get_test_data_dir() / filename


def get_repo_root() -> Path:
    """Resolve this repo's root (parent of the `tests/` directory)."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def gtest_include_path() -> Path:
    """Return the west-installed gtest include directory, skipping the test if absent."""
    path = get_repo_root() / "build" / "gtest" / "googletest" / "include"
    if not path.is_dir():
        pytest.skip(f"GTest headers not found at {path}. Run `pypeline run --step WestInstall` first.")
    return path


def make_compile_commands(tmp_path: Path, source_file: Path, include_paths: Iterable[Path]) -> Path:
    """Write a minimal `compile_commands.json` referencing `source_file` with `-I` include paths."""
    include_args = " ".join(f"-I{path}" for path in include_paths)
    entry = {
        "directory": str(tmp_path),
        "file": str(source_file),
        "command": f"clang++ {include_args} -c {source_file}",
    }
    path = tmp_path / "compile_commands.json"
    path.write_text(json.dumps([entry]))
    return path
