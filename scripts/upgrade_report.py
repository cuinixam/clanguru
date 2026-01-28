import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from clanguru.object_analyzer import get_html_template_path


def build_tree_from_nodes(nodes_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Reconstruct the tree structure from a list of directory nodes (size=0).

    nodes_data: List of dicts, each is the 'data' part of a node definition.
    """
    # Filter for directory nodes (size == 0)
    # The input 'nodes_data' is expecting the list of 'data' dictionaries directly?
    # Or the full node objects with 'data' key?
    # Let's assume we pass the list of 'data' dicts for directory nodes only.

    # We need to turn flat paths "A/B/C" into a nested tree.
    # Map path -> tree_node
    # tree_node = { 'id': path, 'name': name, 'children': [] }

    # First, collect all directory paths and create node objects for them
    path_to_node = {}
    roots = []

    # Get all directory nodes data
    dir_nodes = [n["data"] for n in nodes_data if n["data"].get("size", 0) == 0]

    # Create tree node objects for all directories
    for d in dir_nodes:
        node_id = d["id"]
        node_name = d.get("content") or d.get("label") or d["id"]
        # Note: 'content' in graph data often holds the name (e.g. "drivers") while 'id' is path

        path_to_node[node_id] = {
            "id": node_id,
            "name": node_name,  # Use the label/content as name
            "children": [],
        }

    # Now link them up based on 'parent' field
    for d in dir_nodes:
        node_id = d["id"]
        parent_id = d.get("parent")

        current_node = path_to_node[node_id]

        if parent_id and parent_id in path_to_node:
            path_to_node[parent_id]["children"].append(current_node)
        else:
            # If no parent, or parent not in our set of directories, it's a root
            roots.append(current_node)

    # ---------------------------------------------------------
    # Handle root-level files (files with no parent directory)
    # ---------------------------------------------------------
    # These are files that don't belong to any component/directory in the graph structure
    file_nodes = [n["data"] for n in nodes_data if n["data"].get("size", 0) > 0]

    for f in file_nodes:
        parent_id = f.get("parent")
        # If it has no parent, OR its parent is not in our directory map (though that shouldn't happen if structure is valid)
        if not parent_id:
            # Create a leaf node for this file
            file_node = {
                "id": f["id"],
                "name": f.get("content") or f.get("label") or f["id"],
                "children": [],  # Files have no children in the filter tree
            }
            roots.append(file_node)

    return roots


def main() -> None:
    parser = argparse.ArgumentParser(description="Upgrade/Regenerate Clanguru Object Analysis Report")
    parser.add_argument("input_file", type=Path, help="Input HTML report file (old version)")
    parser.add_argument("output_file", type=Path, help="Output HTML report file (new version)")

    args = parser.parse_args()

    input_file = args.input_file
    output_file = args.output_file

    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        sys.exit(1)

    template_file = get_html_template_path()
    print(f"Using template: {template_file}")

    content = input_file.read_text(encoding="utf-8")

    # Extract JSON
    match = re.search(r"var MY_GRAPH_DATA = ({.*?});", content, re.DOTALL)
    if not match:
        print("Error: Could not find MY_GRAPH_DATA in input file.")
        sys.exit(1)

    json_str = match.group(1)
    try:
        graph_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        sys.exit(1)

    print(f"Loaded graph data: {len(graph_data.get('nodes', []))} nodes, {len(graph_data.get('edges', []))} edges.")

    # generate tree
    tree = build_tree_from_nodes(graph_data["nodes"])
    graph_data["tree"] = tree
    print(f"Generated filter tree with {len(tree)} root items.")

    # Render template
    env = Environment(loader=FileSystemLoader(template_file.parent), autoescape=True)
    template = env.get_template(template_file.name)
    rendered_html = template.render(graph_data=graph_data)

    output_file.write_text(rendered_html, encoding="utf-8")
    print(f"Successfully generated {output_file}")


if __name__ == "__main__":
    main()
