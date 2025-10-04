"""Tests for external symbol filtering functionality."""

from pathlib import Path

from clanguru.object_analyzer import ObjectDependencies, Symbol, SymbolLinkage, filter_external_symbols_only


def test_filter_external_symbols_only_basic() -> None:
    """Test filter_external_symbols_only with mixed symbol types."""
    obj1 = ObjectDependencies(Path("test1.o"))
    obj1.symbols = [
        Symbol("main", SymbolLinkage.LOCAL),  # Should be filtered out
        Symbol("helper_func", SymbolLinkage.LOCAL),  # Should be filtered out
        Symbol("printf", SymbolLinkage.EXTERN),  # Should be kept
        Symbol("malloc", SymbolLinkage.EXTERN),  # Should be kept
    ]

    object_data = [obj1]

    filtered = filter_external_symbols_only(object_data)
    assert len(filtered) == 1

    # Should only keep EXTERN symbols
    assert len(filtered[0].symbols) == 2
    symbol_names = {s.name for s in filtered[0].symbols}
    assert symbol_names == {"printf", "malloc"}

    # Verify all remaining symbols are EXTERN
    for symbol in filtered[0].symbols:
        assert symbol.linkage == SymbolLinkage.EXTERN


def test_filter_external_symbols_only_multiple_objects() -> None:
    """Test filter_external_symbols_only with multiple objects."""
    obj1 = ObjectDependencies(Path("test1.o"))
    obj1.symbols = [
        Symbol("main", SymbolLinkage.LOCAL),
        Symbol("printf", SymbolLinkage.EXTERN),
        Symbol("local_helper", SymbolLinkage.LOCAL),
    ]

    obj2 = ObjectDependencies(Path("test2.o"))
    obj2.symbols = [
        Symbol("calculate", SymbolLinkage.LOCAL),
        Symbol("malloc", SymbolLinkage.EXTERN),
        Symbol("free", SymbolLinkage.EXTERN),
    ]

    obj3 = ObjectDependencies(Path("test3.o"))
    obj3.symbols = [
        Symbol("internal_func", SymbolLinkage.LOCAL),
        Symbol("static_var", SymbolLinkage.LOCAL),
    ]

    object_data = [obj1, obj2, obj3]

    filtered = filter_external_symbols_only(object_data)
    assert len(filtered) == 3

    # Check obj1 - should only have printf
    assert len(filtered[0].symbols) == 1
    assert filtered[0].symbols[0].name == "printf"
    assert filtered[0].symbols[0].linkage == SymbolLinkage.EXTERN

    # Check obj2 - should have malloc and free
    assert len(filtered[1].symbols) == 2
    obj2_symbol_names = {s.name for s in filtered[1].symbols}
    assert obj2_symbol_names == {"malloc", "free"}
    for symbol in filtered[1].symbols:
        assert symbol.linkage == SymbolLinkage.EXTERN

    # Check obj3 - should have no symbols (all were LOCAL)
    assert len(filtered[2].symbols) == 0


def test_filter_external_symbols_only_all_local() -> None:
    """Test filter_external_symbols_only when all symbols are local."""
    obj1 = ObjectDependencies(Path("test1.o"))
    obj1.symbols = [
        Symbol("main", SymbolLinkage.LOCAL),
        Symbol("helper", SymbolLinkage.LOCAL),
        Symbol("internal", SymbolLinkage.LOCAL),
    ]

    object_data = [obj1]

    filtered = filter_external_symbols_only(object_data)
    assert len(filtered) == 1
    assert len(filtered[0].symbols) == 0  # All symbols should be filtered out


def test_filter_external_symbols_only_all_external() -> None:
    """Test filter_external_symbols_only when all symbols are external."""
    obj1 = ObjectDependencies(Path("test1.o"))
    obj1.symbols = [
        Symbol("printf", SymbolLinkage.EXTERN),
        Symbol("malloc", SymbolLinkage.EXTERN),
        Symbol("free", SymbolLinkage.EXTERN),
    ]

    object_data = [obj1]

    filtered = filter_external_symbols_only(object_data)
    assert len(filtered) == 1
    assert len(filtered[0].symbols) == 3  # All symbols should be kept

    symbol_names = {s.name for s in filtered[0].symbols}
    assert symbol_names == {"printf", "malloc", "free"}


def test_filter_external_symbols_only_no_symbols() -> None:
    """Test filter_external_symbols_only with objects that have no symbols."""
    obj1 = ObjectDependencies(Path("empty1.o"))
    obj1.symbols = []

    obj2 = ObjectDependencies(Path("empty2.o"))
    obj2.symbols = []

    object_data = [obj1, obj2]

    filtered = filter_external_symbols_only(object_data)
    assert len(filtered) == 2
    assert len(filtered[0].symbols) == 0
    assert len(filtered[1].symbols) == 0


def test_filter_external_symbols_only_empty_object_list() -> None:
    """Test filter_external_symbols_only with empty object list."""
    filtered = filter_external_symbols_only([])
    assert len(filtered) == 0


def test_filter_external_symbols_only_preserves_object_properties() -> None:
    """Test that filter_external_symbols_only creates new instances and preserves ObjectData properties."""
    original_obj = ObjectDependencies(Path("original/test.o"))
    original_obj.symbols = [
        Symbol("main", SymbolLinkage.LOCAL),
        Symbol("printf", SymbolLinkage.EXTERN),
        Symbol("helper", SymbolLinkage.LOCAL),
    ]

    object_data = [original_obj]

    # Filter the data
    filtered = filter_external_symbols_only(object_data)

    assert len(filtered) == 1
    filtered_obj = filtered[0]

    # Verify it's a new instance
    assert filtered_obj is not original_obj
    assert filtered_obj.symbols is not original_obj.symbols

    # Verify path is preserved
    assert filtered_obj.path == original_obj.path
    assert filtered_obj.name == original_obj.name

    # Verify only external symbols remain
    assert len(filtered_obj.symbols) == 1
    assert filtered_obj.symbols[0].name == "printf"
    assert filtered_obj.symbols[0].linkage == SymbolLinkage.EXTERN


def test_filter_external_symbols_only_cached_properties() -> None:
    """Test that filtered ObjectData instances have fresh cached property values."""
    obj = ObjectDependencies(Path("test.o"))
    obj.symbols = [
        Symbol("provided_func", SymbolLinkage.LOCAL),  # Will be filtered out
        Symbol("required_func", SymbolLinkage.EXTERN),  # Will be kept
        Symbol("another_local", SymbolLinkage.LOCAL),  # Will be filtered out
        Symbol("another_extern", SymbolLinkage.EXTERN),  # Will be kept
    ]

    # Access cached properties on original to populate cache
    original_provided = obj.provided_symbols  # Should include provided_func, another_local
    original_required = obj.required_symbols  # Should include required_func, another_extern

    assert len(original_provided) == 2  # LOCAL symbols
    assert len(original_required) == 2  # EXTERN symbols

    # Filter the data
    filtered = filter_external_symbols_only([obj])
    filtered_obj = filtered[0]

    # Check that cached properties are recalculated
    filtered_provided = filtered_obj.provided_symbols
    filtered_required = filtered_obj.required_symbols

    # After filtering, we only have EXTERN symbols, so:
    # - provided_symbols should be empty (no LOCAL symbols left)
    # - required_symbols should contain both external symbols
    assert len(filtered_provided) == 0  # No LOCAL symbols left
    assert len(filtered_required) == 2  # Both EXTERN symbols remain
    assert "required_func" in filtered_required
    assert "another_extern" in filtered_required
