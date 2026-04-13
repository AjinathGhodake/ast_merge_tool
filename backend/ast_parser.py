"""
AST Parser Module
Parses Python code into AST and extracts structural information.
"""

import ast
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class NodeType(str, Enum):
    IMPORT = "import"
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    OTHER = "other"


@dataclass
class CodeNode:
    """Represents a parsed code element."""

    name: str
    node_type: NodeType
    start_line: int
    end_line: int
    source: str
    signature: str = ""
    parent: Optional[str] = None
    dependencies: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "node_type": self.node_type.value,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "source": self.source,
            "signature": self.signature,
            "parent": self.parent,
            "dependencies": self.dependencies,
            "children": self.children,
        }


@dataclass
class ParsedCode:
    """Container for parsed code structure."""

    source: str
    nodes: dict[str, CodeNode] = field(default_factory=dict)
    imports: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "imports": self.imports,
        }


class ASTParser:
    """Parses Python source code into structured AST nodes."""

    def __init__(self, source: str):
        self.source = source
        self.lines = source.split("\n")
        self.tree = ast.parse(source)

    def parse(self) -> ParsedCode:
        """Parse the source code and extract all nodes."""
        parsed = ParsedCode(source=self.source)

        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._extract_import(node, parsed)
            elif isinstance(node, ast.FunctionDef):
                self._extract_function(node, parsed)
            elif isinstance(node, ast.AsyncFunctionDef):
                self._extract_function(node, parsed, is_async=True)
            elif isinstance(node, ast.ClassDef):
                self._extract_class(node, parsed)

        return parsed

    def _get_source_segment(self, node: ast.AST) -> str:
        """Extract source code for a given AST node."""
        try:
            return ast.get_source_segment(self.source, node) or ""
        except:
            # Fallback to line-based extraction
            start = node.lineno - 1
            end = getattr(node, "end_lineno", start + 1)
            return "\n".join(self.lines[start:end])

    def _extract_import(self, node: ast.AST, parsed: ParsedCode):
        """Extract import statements."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                parsed.imports.append(name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                name = alias.asname or alias.name
                parsed.imports.append(f"{module}.{name}" if module else name)

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parsed: ParsedCode,
        is_async: bool = False,
        parent: Optional[str] = None,
    ):
        """Extract function definition."""
        name = node.name
        full_name = f"{parent}.{name}" if parent else name

        # Build signature
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except:
                    pass
            args.append(arg_str)

        signature = f"{'async ' if is_async else ''}def {name}({', '.join(args)})"
        if node.returns:
            try:
                signature += f" -> {ast.unparse(node.returns)}"
            except:
                pass

        # Extract dependencies (names used in the function)
        deps = self._extract_dependencies(node)

        code_node = CodeNode(
            name=full_name,
            node_type=NodeType.METHOD if parent else NodeType.FUNCTION,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            source=self._get_source_segment(node),
            signature=signature,
            parent=parent,
            dependencies=deps,
        )

        parsed.nodes[full_name] = code_node

    def _extract_class(self, node: ast.ClassDef, parsed: ParsedCode):
        """Extract class definition with its methods."""
        name = node.name

        # Get base classes
        bases = []
        for base in node.bases:
            try:
                bases.append(ast.unparse(base))
            except:
                pass

        signature = f"class {name}"
        if bases:
            signature += f"({', '.join(bases)})"

        # Extract methods
        children = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_name = f"{name}.{item.name}"
                children.append(method_name)
                self._extract_function(
                    item,
                    parsed,
                    is_async=isinstance(item, ast.AsyncFunctionDef),
                    parent=name,
                )

        code_node = CodeNode(
            name=name,
            node_type=NodeType.CLASS,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            source=self._get_source_segment(node),
            signature=signature,
            children=children,
            dependencies=self._extract_dependencies(node),
        )

        parsed.nodes[name] = code_node

    def _extract_dependencies(self, node: ast.AST) -> list[str]:
        """Extract names that this node depends on."""
        deps = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                deps.add(child.id)
            elif isinstance(child, ast.Attribute):
                # Get the root name of attribute access
                current = child
                while isinstance(current, ast.Attribute):
                    current = current.value
                if isinstance(current, ast.Name):
                    deps.add(current.id)
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    deps.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    deps.add(child.func.attr)

        return list(deps)


def parse_code(source: str) -> ParsedCode:
    """Convenience function to parse source code."""
    parser = ASTParser(source)
    return parser.parse()
