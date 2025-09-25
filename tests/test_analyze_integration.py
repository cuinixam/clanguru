"""Integration test for the analyze command functionality."""

from pathlib import Path

from clanguru.object_analyzer import ObjectData, Symbol, SymbolLinkage, filter_external_symbols_only, filter_object_data_symbols


def test_analyze_command_filtering_integration() -> None:
    """Test the complete filtering pipeline used by analyze command."""
    # Create test data that simulates what parse_objects would return
    original_data = [
        ObjectData(
            path=Path("test1.o"),
            symbols=[
                # LOCAL symbols - should be filtered out by external filtering
                Symbol("main", SymbolLinkage.LOCAL),
                Symbol("helper_func", SymbolLinkage.LOCAL),
                Symbol("_local_internal", SymbolLinkage.LOCAL),
                # EXTERN symbols - should survive external filtering
                Symbol("printf", SymbolLinkage.EXTERN),
                Symbol("malloc", SymbolLinkage.EXTERN),
                Symbol("_external_debug", SymbolLinkage.EXTERN),  # Should be excluded by pattern
                Symbol("_external_internal", SymbolLinkage.EXTERN),  # Should be excluded by pattern
                Symbol("valid_dependency", SymbolLinkage.EXTERN),
            ],
        ),
        ObjectData(
            path=Path("test2.o"),
            symbols=[
                Symbol("static_func", SymbolLinkage.LOCAL),
                Symbol("free", SymbolLinkage.EXTERN),
                Symbol("_system_call", SymbolLinkage.EXTERN),  # Should be excluded by pattern
            ],
        ),
    ]

    # Step 1: Apply external symbol filtering (as analyze command does)
    external_filtered = filter_external_symbols_only(original_data)

    # Verify that only EXTERN symbols remain
    assert len(external_filtered) == 2

    # Check first object - should have 4 EXTERN symbols
    obj1_symbols = {s.name for s in external_filtered[0].symbols}
    expected_obj1_extern = {"printf", "malloc", "_external_debug", "_external_internal", "valid_dependency"}
    assert obj1_symbols == expected_obj1_extern

    # Check second object - should have 2 EXTERN symbols
    obj2_symbols = {s.name for s in external_filtered[1].symbols}
    expected_obj2_extern = {"free", "_system_call"}
    assert obj2_symbols == expected_obj2_extern

    # All remaining symbols should be EXTERN
    for obj in external_filtered:
        for symbol in obj.symbols:
            assert symbol.linkage == SymbolLinkage.EXTERN

    # Step 2: Apply exclude pattern filtering (as analyze command does when patterns provided)
    exclude_patterns = ["_*"]
    pattern_filtered = filter_object_data_symbols(external_filtered, exclude_patterns)

    # Verify that symbols matching _* pattern are excluded
    assert len(pattern_filtered) == 2

    # Check first object - should exclude _external_debug and _external_internal
    obj1_final_symbols = {s.name for s in pattern_filtered[0].symbols}
    expected_obj1_final = {"printf", "malloc", "valid_dependency"}
    assert obj1_final_symbols == expected_obj1_final

    # Check second object - should exclude _system_call
    obj2_final_symbols = {s.name for s in pattern_filtered[1].symbols}
    expected_obj2_final = {"free"}
    assert obj2_final_symbols == expected_obj2_final

    # All remaining symbols should still be EXTERN
    for obj in pattern_filtered:
        for symbol in obj.symbols:
            assert symbol.linkage == SymbolLinkage.EXTERN


def test_analyze_command_filtering_no_exclude_patterns() -> None:
    """Test analyze command filtering when no exclude patterns are provided."""
    # Create test data
    original_data = [
        ObjectData(
            path=Path("test.o"),
            symbols=[
                Symbol("main", SymbolLinkage.LOCAL),  # Should be filtered out
                Symbol("printf", SymbolLinkage.EXTERN),  # Should be kept
                Symbol("_debug", SymbolLinkage.EXTERN),  # Should be kept (no patterns applied)
            ],
        )
    ]

    # Step 1: Apply external symbol filtering only
    external_filtered = filter_external_symbols_only(original_data)

    # Should keep only EXTERN symbols
    assert len(external_filtered) == 1
    symbol_names = {s.name for s in external_filtered[0].symbols}
    assert symbol_names == {"printf", "_debug"}

    # Step 2: No pattern filtering applied when patterns are None/empty
    pattern_filtered = filter_object_data_symbols(external_filtered, None)

    # Should be the same as external_filtered
    assert len(pattern_filtered) == 1
    final_symbol_names = {s.name for s in pattern_filtered[0].symbols}
    assert final_symbol_names == {"printf", "_debug"}


def test_analyze_command_filtering_empty_patterns() -> None:
    """Test analyze command filtering when empty exclude patterns are provided."""
    original_data = [
        ObjectData(
            path=Path("test.o"),
            symbols=[
                Symbol("main", SymbolLinkage.LOCAL),
                Symbol("printf", SymbolLinkage.EXTERN),
                Symbol("_debug", SymbolLinkage.EXTERN),
            ],
        )
    ]

    # Apply external filtering
    external_filtered = filter_external_symbols_only(original_data)

    # Apply empty pattern filtering
    pattern_filtered = filter_object_data_symbols(external_filtered, [])

    # Should keep all EXTERN symbols
    assert len(pattern_filtered) == 1
    symbol_names = {s.name for s in pattern_filtered[0].symbols}
    assert symbol_names == {"printf", "_debug"}
