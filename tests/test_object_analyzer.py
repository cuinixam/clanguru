from pathlib import Path

import pytest

from clanguru.compilation_options_manager import CompileCommand
from clanguru.object_analyzer import (
    NmExecutor,
    ObjectDependencies,
    ObjectReportData,
    Symbol,
    SymbolLinkage,
    collapse_objects_report_data_tree,
    create_objects_graph_data_nodes,
    create_objects_report_data_tree,
    create_objects_report_data_tree_expanded,
)


@pytest.mark.parametrize(
    "line, expected_name, expected_linkage",
    [
        # Undefined (EXTERN)
        ("                 U __imp_GetAsyncKeyState", "__imp_GetAsyncKeyState", SymbolLinkage.EXTERN),
        ("                 U another_undefined", "another_undefined", SymbolLinkage.EXTERN),
        # LOCAL symbols
        ("0000000000000130 T RteGetBrightnessValue", "RteGetBrightnessValue", SymbolLinkage.LOCAL),
        ("0000000000000000 D _data_symbol", "_data_symbol", SymbolLinkage.LOCAL),
        ("0000000000000008 B _bss_symbol", "_bss_symbol", SymbolLinkage.LOCAL),
        ("0000000000000004 R _ro_symbol", "_ro_symbol", SymbolLinkage.LOCAL),
        ("000000000000000c A _abs_symbol", "_abs_symbol", SymbolLinkage.LOCAL),
        ("                 W _weak_obj", "_weak_obj", SymbolLinkage.LOCAL),
        ("                 V _weak_ref", "_weak_ref", SymbolLinkage.LOCAL),
        ("                 C common_symbol", "common_symbol", SymbolLinkage.LOCAL),
        # Lowercase symbols (should not match the new regex)
        ("0000000000000014 b brightnessValue", None, None),
        ("0000000000000020 t local_text", None, None),
        ("                 w _weak_undef_obj", None, None),
        ("                 v _weak_undef_ref", None, None),
        # Invalid / Non-matching lines
        ("garbage line without match", None, None),
        ("0000000000000000 ? question_mark", None, None),  # ? is not uppercase
    ],
)
def test_get_symbol_various(line, expected_name, expected_linkage):
    result = NmExecutor.get_symbol(line)

    if expected_name is None:
        assert result is None
    else:
        # must be a Symbol with the right fields
        assert isinstance(result, Symbol)
        assert result.name == expected_name
        assert result.linkage == expected_linkage


@pytest.mark.parametrize(
    "paths, expected_common_path_str",
    [
        (
            [
                "some/common/path/dir1/CMakeFiles/a.o",
                "some/common/path/dir1/CMakeFiles/b.o",
            ],
            "some/common/path",
        ),
        (
            [
                "some/common/path/dir1/CMakeFiles/a.o",
                "some/common/path/dir2/CMakeFiles/b.o",
            ],
            "some/common/path",
        ),
        (
            [
                "some/common/path/dir1/CMakeFiles/a.o",
                "some/common/path/dir2/dir21/CMakeFiles/b.o",
                "some/common/path/dir3/dir21/CMakeFiles/b.o",
            ],
            "some/common/path",
        ),
    ],
)
def create_object_path(file_name: str, rel_path: str | None = None) -> Path:
    """Helper function to create a Path object from a string."""
    return Path(rel_path or "some/common/path/dir1/CMakeFiles").joinpath(file_name).absolute()


def create_object_report_data(file_name: str, symbols: list[Symbol], rel_path: str | None = None) -> ObjectReportData:
    """Helper function to create ObjectReportData with mock CompileCommand."""
    object_path = create_object_path(file_name, rel_path)
    source_path = object_path.with_suffix(".c")  # Assume .c source for .o object

    # Create mock CompileCommand
    compile_command = CompileCommand(
        directory=object_path.parent,
        file=source_path,
        command=f"gcc -c {source_path} -o {object_path}",
    )

    # Create ObjectDependencies
    object_dependencies = ObjectDependencies(path=object_path, symbols=symbols)

    return ObjectReportData(object_dependencies=object_dependencies, compile_command=compile_command)


@pytest.fixture
def object_report_data_list(tmp_path: Path) -> tuple[Path, list[ObjectReportData]]:
    project_directory = tmp_path / "my" / "project"
    object_report_data = [
        ObjectReportData(
            object_dependencies=ObjectDependencies(path=project_directory / "build/components/comp_a/src/CMakeFiles/comp_a.o", symbols=[]),
            compile_command=CompileCommand(
                directory=project_directory,
                file=project_directory / "components/comp_a/src/comp_a.c",
                command="gcc ...",
            ),
        ),
        ObjectReportData(
            object_dependencies=ObjectDependencies(path=project_directory / "build/components/comp_b/src/CMakeFiles/comp_b.o", symbols=[]),
            compile_command=CompileCommand(
                directory=project_directory,
                file=project_directory / "components/comp_b/src/comp_b.c",
                command="gcc ...",
            ),
        ),
        ObjectReportData(
            object_dependencies=ObjectDependencies(path=project_directory / "build/mcal/src/CMakeFiles/mcal.o", symbols=[]),
            compile_command=CompileCommand(
                directory=project_directory,
                file=project_directory / "mcal/src/mcal.c",
                command="gcc ...",
            ),
        ),
        ObjectReportData(
            object_dependencies=ObjectDependencies(path=project_directory / "build/mcal/src/drivers/CMakeFiles/adc.o", symbols=[]),
            compile_command=CompileCommand(
                directory=project_directory,
                file=project_directory / "mcal/src/drivers/src/adc.c",
                command="gcc ...",
            ),
        ),
        ObjectReportData(
            object_dependencies=ObjectDependencies(path=project_directory / "build/mcal/src/drivers/CMakeFiles/io.o", symbols=[]),
            compile_command=CompileCommand(
                directory=project_directory,
                file=project_directory / "mcal/src/drivers/src/io.c",
                command="gcc ...",
            ),
        ),
    ]
    return project_directory, object_report_data


def test_create_objects_report_data_tree(object_report_data_list: tuple[Path, list[ObjectReportData]]) -> None:
    # Define a list of object report data based on the user's example
    project_directory, objects = object_report_data_list

    # Generate the tree
    full_tree = create_objects_report_data_tree_expanded(objects)

    # Assert
    assert full_tree is not None
    assert full_tree.name is None  # Root node has no name
    assert {"components", "mcal"} == {child.name for child in full_tree.children}
    # Check components subtree
    components_node = next(child for child in full_tree.children if child.name == "components")
    assert components_node.path.rel_path == Path("components")
    assert components_node.path.full_path == project_directory / "components"
    assert {"comp_a", "comp_b"} == {child.name for child in components_node.children}
    comp_a_node = next(child for child in components_node.children if child.name == "comp_a")
    assert len(comp_a_node.objects) == 0
    comp_a_src_node = next(child for child in comp_a_node.children if child.name == "src")
    assert len(comp_a_src_node.objects) == 1
    assert comp_a_src_node.objects[0].compile_command.file.name == "comp_a.c"
    comp_b_node = next(child for child in components_node.children if child.name == "comp_b")
    assert len(comp_b_node.objects) == 0
    comp_b_src_node = next(child for child in comp_b_node.children if child.name == "src")
    assert len(comp_b_src_node.objects) == 1
    assert comp_b_src_node.objects[0].compile_command.file.name == "comp_b.c"
    # Check mcal subtree
    mcal_node = next(child for child in full_tree.children if child.name == "mcal")
    assert len(mcal_node.objects) == 0
    assert {"src"} == {child.name for child in mcal_node.children}
    mcal_src_node = next(child for child in mcal_node.children if child.name == "src")
    assert {"drivers"} == {child.name for child in mcal_src_node.children}
    assert len(mcal_src_node.children) == 1
    assert len(mcal_src_node.objects) == 1
    assert mcal_src_node.objects[0].compile_command.file.name == "mcal.c"
    drivers_node = next(child for child in mcal_src_node.children if child.name == "drivers")
    assert len(drivers_node.children) == 1
    assert len(drivers_node.objects) == 0
    assert {"src"} == {child.name for child in drivers_node.children}
    drivers_src_node = next(child for child in drivers_node.children if child.name == "src")
    assert len(drivers_src_node.children) == 0
    assert len(drivers_src_node.objects) == 2
    assert {obj.compile_command.file.name for obj in drivers_src_node.objects} == {"adc.c", "io.c"}

    collapsed_tree = collapse_objects_report_data_tree(full_tree)

    # Assert collapsed tree structure
    assert collapsed_tree is not None
    assert collapsed_tree.name is None  # Root node has no name
    assert {"components", "mcal/src"} == {child.name for child in collapsed_tree.children}
    # Check components subtree
    components_node = next(child for child in collapsed_tree.children if child.name == "components")
    assert components_node.path.rel_path == Path("components")
    assert components_node.path.full_path == project_directory / "components"
    assert components_node.path.root_path == project_directory
    assert len(components_node.children) == 0
    assert len(components_node.objects) == 2
    assert {obj.compile_command.file.name for obj in components_node.objects} == {"comp_a.c", "comp_b.c"}
    # Check mcal subtree
    mcal_node = next(child for child in collapsed_tree.children if child.name == "mcal/src")
    assert len(mcal_node.children) == 1
    assert len(mcal_node.objects) == 1
    assert {obj.compile_command.file.name for obj in mcal_node.objects} == {"mcal.c"}
    drivers_node = next(child for child in mcal_node.children if child.name == "drivers/src")
    assert len(drivers_node.children) == 0
    assert len(drivers_node.objects) == 2
    assert drivers_node.path.rel_path == Path("mcal/src/drivers/src")
    assert drivers_node.path.full_path == project_directory / "mcal/src/drivers/src"
    assert drivers_node.path.root_path == project_directory
    assert {obj.compile_command.file.name for obj in drivers_node.objects} == {"adc.c", "io.c"}


def test_create_objects_graph_data_nodes(object_report_data_list: tuple[Path, list[ObjectReportData]]) -> None:
    _, objects = object_report_data_list
    nodes = create_objects_graph_data_nodes(create_objects_report_data_tree(objects), {}, exclude_isolated_objects=False)
    # Assert
    assert len(nodes) == 8
    assert {node.data.label for node in nodes} == {
        "components",
        "comp_a/src/comp_a.c",
        "comp_b/src/comp_b.c",
        "mcal/src",
        "mcal.c",
        "drivers/src",
        "adc.c",
        "io.c",
    }
    # The ids are whole relative path
    assert {node.data.id for node in nodes} == {
        "components",
        "components/comp_a/src/comp_a.c",
        "components/comp_b/src/comp_b.c",
        "mcal/src",
        "mcal/src/mcal.c",
        "mcal/src/drivers/src",
        "mcal/src/drivers/src/adc.c",
        "mcal/src/drivers/src/io.c",
    }
