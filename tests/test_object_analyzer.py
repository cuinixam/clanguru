from pathlib import Path

import pytest

from clanguru.object_analyzer import NmExecutor, ObjectData, ObjectsDependenciesReportGenerator, Symbol, SymbolLinkage


@pytest.mark.parametrize(
    "line, expected_name, expected_linkage",
    [
        # undefined externals
        ("                 U __imp_GetAsyncKeyState", "__imp_GetAsyncKeyState", SymbolLinkage.EXTERN),
        # defined text symbols => LOCAL (per your mapping)
        ("0000000000000130 T RteGetBrightnessValue", "RteGetBrightnessValue", SymbolLinkage.LOCAL),
        # lowercase 'b' isn't in the current patterns => None
        ("0000000000000014 b brightnessValue", None, None),
        # completely unrelated line => None
        ("garbage line without match", None, None),
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
