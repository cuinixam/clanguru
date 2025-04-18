from pathlib import Path

import pytest

from clanguru.object_analyzer import NmExecutor, ObjectData, ObjectsDependenciesReportGenerator, Symbol, SymbolLinkage


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


def test_generate_graph_data_basic_dependency_pytest():
    """Pytest: Test graph generation with a simple dependency."""
    # Note: ObjectData now calculates provided/required symbols via cached_property
    obj_a = ObjectData(Path("a.o"), symbols=[Symbol("func1", SymbolLinkage.LOCAL), Symbol("func2", SymbolLinkage.EXTERN)])
    obj_b = ObjectData(Path("b.o"), symbols=[Symbol("func2", SymbolLinkage.LOCAL), Symbol("func1", SymbolLinkage.EXTERN)])
    objects = [obj_a, obj_b]
    graph_data = ObjectsDependenciesReportGenerator.generate_graph_data(objects)

    assert len(graph_data["nodes"]) == 2
    assert len(graph_data["edges"]) == 1

    node_map = {n["data"]["id"]: n["data"] for n in graph_data["nodes"]}
    assert node_map["a.o"]["size"] == 7  # Base 5 + 1 connection * 2
    assert node_map["b.o"]["size"] == 7  # Base 5 + 1 connection * 2

    edge = graph_data["edges"][0]["data"]
    assert edge["id"] == "a.o.b.o"
    assert edge["source"] in ["a.o", "b.o"]
    assert edge["target"] in ["a.o", "b.o"]
    assert edge["source"] != edge["target"]


def test_generate_graph_data_no_dependency_pytest():
    """Pytest: Test graph generation with no dependencies."""
    obj_a = ObjectData(Path("a.o"), symbols=[Symbol("func1", SymbolLinkage.LOCAL), Symbol("funcX", SymbolLinkage.EXTERN)])
    obj_b = ObjectData(Path("b.o"), symbols=[Symbol("func2", SymbolLinkage.LOCAL), Symbol("funcY", SymbolLinkage.EXTERN)])
    objects = [obj_a, obj_b]
    graph_data = ObjectsDependenciesReportGenerator.generate_graph_data(objects)

    assert len(graph_data["nodes"]) == 2
    assert len(graph_data["edges"]) == 0

    node_map = {n["data"]["id"]: n["data"] for n in graph_data["nodes"]}
    assert node_map["a.o"]["size"] == 5  # Base 5 + 0 connections * 2
    assert node_map["b.o"]["size"] == 5  # Base 5 + 0 connections * 2


def test_generate_graph_data_complex_dependencies_pytest():
    """Pytest: Test graph generation with multiple dependencies."""
    obj_a = ObjectData(
        Path("a.o"), symbols=[Symbol("funcA", SymbolLinkage.LOCAL), Symbol("funcB", SymbolLinkage.EXTERN), Symbol("funcC", SymbolLinkage.EXTERN)]
    )  # Provides A, Requires B, C
    obj_b = ObjectData(Path("b.o"), symbols=[Symbol("funcB", SymbolLinkage.LOCAL), Symbol("funcA", SymbolLinkage.EXTERN)])  # Provides B, Requires A
    obj_c = ObjectData(Path("c.o"), symbols=[Symbol("funcC", SymbolLinkage.LOCAL)])  # Provides C, Requires nothing
    obj_d = ObjectData(Path("d.o"), symbols=[Symbol("funcD", SymbolLinkage.LOCAL), Symbol("funcE", SymbolLinkage.EXTERN)])  # Provides D, Requires E (isolated)
    objects = [obj_a, obj_b, obj_c, obj_d]
    graph_data = ObjectsDependenciesReportGenerator.generate_graph_data(objects)

    assert len(graph_data["nodes"]) == 4
    assert len(graph_data["edges"]) == 2  # A<->B, A<->C

    node_map = {n["data"]["id"]: n["data"] for n in graph_data["nodes"]}
    # Connections: A: 2 (B, C), B: 1 (A), C: 1 (A), D: 0
    assert node_map["a.o"]["size"] == 9  # 5 + 2*2
    assert node_map["b.o"]["size"] == 7  # 5 + 1*2
    assert node_map["c.o"]["size"] == 7  # 5 + 1*2
    assert node_map["d.o"]["size"] == 5  # 5 + 0*2

    edge_ids = {e["data"]["id"] for e in graph_data["edges"]}
    assert "a.o.b.o" in edge_ids
    assert "a.o.c.o" in edge_ids
