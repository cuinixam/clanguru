import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader
from py_app_dev.core.subprocess import SubprocessExecutor


class SymbolLinkage(Enum):
    EXTERN = auto()
    LOCAL = auto()


@dataclass
class Symbol:
    name: str
    linkage: SymbolLinkage


@dataclass
class ObjectData:
    path: Path
    symbols: list[Symbol] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.path.name

    @cached_property
    def required_symbols(self) -> set[str]:
        """Collects all EXTERN symbols into a set."""
        return {symbol.name for symbol in self.symbols if symbol.linkage == SymbolLinkage.EXTERN}

    @cached_property
    def provided_symbols(self) -> set[str]:
        """Collects all LOCAL symbols into a set."""
        return {symbol.name for symbol in self.symbols if symbol.linkage == SymbolLinkage.LOCAL}


class NmExecutor:
    @staticmethod
    def run(obj_file: Path) -> ObjectData:
        obj_data = ObjectData(obj_file)
        executor = SubprocessExecutor(command=["nm", obj_file], capture_output=True, print_output=False)
        completed_process = executor.execute(handle_errors=False)
        if completed_process:
            if completed_process.returncode != 0:
                raise subprocess.CalledProcessError(completed_process.returncode, completed_process.args, stderr=completed_process.stderr)

            # Process the output
            for line in completed_process.stdout.splitlines():
                symbol = NmExecutor.get_symbol(line)
                if symbol:
                    obj_data.symbols.append(symbol)
        else:
            raise UnboundLocalError("nm command failed")
        return obj_data

    @staticmethod
    def get_symbol(nm_symbol_output: str) -> Optional[Symbol]:
        # Regex to capture optional address, mandatory uppercase symbol type, and symbol name
        # Group 1: Symbol Type Letter (e.g., 'U', 'T', 'D', 'B', etc.)
        # Group 2: Symbol Name
        pattern: re.Pattern[str] = re.compile(r"^\s*(?:[0-9A-Fa-f]+\s+)?([A-Z])\s+(\S+)")
        match = pattern.match(nm_symbol_output)

        if match:
            symbol_type_letter = match.group(1)
            symbol_name = match.group(2)

            # Determine linkage based on the symbol type letter
            linkage = SymbolLinkage.EXTERN if symbol_type_letter == "U" else SymbolLinkage.LOCAL

            return Symbol(name=symbol_name, linkage=linkage)

        return None


def parse_objects(obj_files: list[Path], max_workers: Optional[int] = None) -> list[ObjectData]:
    """Run the nm executor on each object file in parallel, collecting all the resulting ObjectData in the same order as `obj_files`."""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        # executor.map preserves input order in its output sequence
        results = list(pool.map(NmExecutor.run, obj_files))

    return results


class ObjectsDependenciesReportGenerator:
    def __init__(self, object_data: list[ObjectData]):
        self.object_data = object_data

    def generate_report(self, output_file: Path) -> None:
        """Generates the HTML report by rendering the Jinja2 template with the graph data."""
        graph_data = self.generate_graph_data(self.object_data)

        env = Environment(loader=FileSystemLoader(Path(__file__).parent), autoescape=True)
        template = env.get_template("object_analyzer.html.jinja")
        rendered_html = template.render(graph_data=graph_data)

        # Write the rendered HTML to the output file
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(rendered_html)

    @staticmethod
    def generate_graph_data(objects: list[ObjectData]) -> dict[str, list[dict[str, Any]]]:
        """Converts a list of ObjectData into a dictionary suitable for Cytoscape.js containing nodes and edges representing object dependencies."""
        nodes = []
        edges = []
        edge_set = set()  # To avoid duplicate edges between the same pair
        node_connections = {obj.name: 0 for obj in objects}

        # Determine edges and count connections
        for i in range(len(objects)):
            for j in range(i + 1, len(objects)):
                obj1 = objects[i]
                obj2 = objects[j]

                # Check if obj1 provides any symbol required by obj2
                provides_required = bool(obj1.provided_symbols.intersection(obj2.required_symbols))
                # Check if obj2 provides any symbol required by obj1
                required_provides = bool(obj2.provided_symbols.intersection(obj1.required_symbols))

                if provides_required or required_provides:
                    # Ensure edge ID is consistent regardless of order
                    source_name, target_name = sorted([obj1.name, obj2.name])
                    edge_id = f"{source_name}.{target_name}"

                    if edge_id not in edge_set:
                        edges.append(
                            {
                                "data": {
                                    "id": edge_id,
                                    "source": obj1.name,  # Cytoscape doesn't strictly enforce source/target for undirected
                                    "target": obj2.name,
                                }
                            }
                        )
                        edge_set.add(edge_id)
                        node_connections[obj1.name] += 1
                        node_connections[obj2.name] += 1

        # Create nodes with size based on connections
        for obj in objects:
            # Use a minimum size for nodes, e.g., 5, or scale based on connections
            # Simple scaling: base_size + connections * scale_factor
            node_size = 5 + node_connections[obj.name] * 2  # Example scaling
            nodes.append(
                {
                    "data": {
                        "id": obj.name,
                        "size": node_size,
                        "content": obj.name,  # Display object name
                        "font_size": 10,  # Adjust font size as needed
                        # parent property is ignored as requested
                    }
                }
            )

        return {"nodes": nodes, "edges": edges}
