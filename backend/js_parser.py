"""
JavaScript AST Parser Module
Parses JavaScript/TypeScript code into AST and extracts structural information.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

try:
    import tree_sitter_javascript as tsjs
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


class NodeType(str, Enum):
    IMPORT = "import"
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    ARROW_FUNCTION = "arrow_function"
    EXPORT = "export"
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
    language: str
    nodes: dict[str, CodeNode] = field(default_factory=dict)
    imports: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "language": self.language,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "imports": self.imports,
        }


class JSParser:
    """Parses JavaScript source code into structured AST nodes."""

    def __init__(self, source: str):
        self.source = source
        self.lines = source.split('\n')
        self.source_bytes = source.encode('utf-8')

        if TREE_SITTER_AVAILABLE:
            self.parser = Parser(Language(tsjs.language()))
            self.tree = self.parser.parse(self.source_bytes)
        else:
            self.parser = None
            self.tree = None

    def parse(self) -> ParsedCode:
        """Parse the source code and extract all nodes."""
        parsed = ParsedCode(source=self.source, language="javascript")

        if self.tree:
            self._walk_tree(self.tree.root_node, parsed)
        else:
            # Fallback to regex-based parsing
            self._regex_parse(parsed)

        return parsed

    def _walk_tree(self, node, parsed: ParsedCode, parent: Optional[str] = None):
        """Walk the tree-sitter AST and extract nodes."""

        if node.type == 'import_statement':
            self._extract_import(node, parsed)

        elif node.type == 'function_declaration':
            self._extract_function(node, parsed, parent)

        elif node.type == 'class_declaration':
            self._extract_class(node, parsed)

        elif node.type == 'lexical_declaration' or node.type == 'variable_declaration':
            self._extract_variable(node, parsed, parent)

        elif node.type == 'export_statement':
            self._extract_export(node, parsed)

        elif node.type == 'method_definition':
            if parent:
                self._extract_method(node, parsed, parent)

        # Recurse into children
        for child in node.children:
            self._walk_tree(child, parsed, parent)

    def _get_node_text(self, node) -> str:
        """Get the source text for a tree-sitter node."""
        return self.source_bytes[node.start_byte:node.end_byte].decode('utf-8')

    def _extract_import(self, node, parsed: ParsedCode):
        """Extract import statement."""
        text = self._get_node_text(node)
        # Extract imported names
        for child in node.children:
            if child.type == 'import_clause':
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        parsed.imports.append(self._get_node_text(subchild))
                    elif subchild.type == 'named_imports':
                        for spec in subchild.children:
                            if spec.type == 'import_specifier':
                                for id_node in spec.children:
                                    if id_node.type == 'identifier':
                                        parsed.imports.append(self._get_node_text(id_node))
                                        break

    def _extract_function(self, node, parsed: ParsedCode, parent: Optional[str] = None):
        """Extract function declaration."""
        name = None
        params = []

        for child in node.children:
            if child.type == 'identifier':
                name = self._get_node_text(child)
            elif child.type == 'formal_parameters':
                params = self._extract_params(child)

        if name:
            full_name = f"{parent}.{name}" if parent else name
            signature = f"function {name}({', '.join(params)})"

            code_node = CodeNode(
                name=full_name,
                node_type=NodeType.METHOD if parent else NodeType.FUNCTION,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                source=self._get_node_text(node),
                signature=signature,
                parent=parent,
                dependencies=self._extract_dependencies(node)
            )
            parsed.nodes[full_name] = code_node

    def _extract_class(self, node, parsed: ParsedCode):
        """Extract class declaration."""
        name = None
        children = []

        for child in node.children:
            if child.type == 'identifier':
                name = self._get_node_text(child)
            elif child.type == 'class_body':
                # Extract methods
                for member in child.children:
                    if member.type == 'method_definition':
                        method_name = None
                        for m_child in member.children:
                            if m_child.type == 'property_identifier':
                                method_name = self._get_node_text(m_child)
                                break
                        if method_name and name:
                            full_method_name = f"{name}.{method_name}"
                            children.append(full_method_name)
                            self._extract_method(member, parsed, name)

        if name:
            code_node = CodeNode(
                name=name,
                node_type=NodeType.CLASS,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                source=self._get_node_text(node),
                signature=f"class {name}",
                children=children,
                dependencies=self._extract_dependencies(node)
            )
            parsed.nodes[name] = code_node

    def _extract_method(self, node, parsed: ParsedCode, parent: str):
        """Extract method from class."""
        name = None
        params = []
        is_async = False

        for child in node.children:
            if child.type == 'property_identifier':
                name = self._get_node_text(child)
            elif child.type == 'formal_parameters':
                params = self._extract_params(child)
            elif self._get_node_text(child) == 'async':
                is_async = True

        if name:
            full_name = f"{parent}.{name}"
            prefix = "async " if is_async else ""
            signature = f"{prefix}{name}({', '.join(params)})"

            code_node = CodeNode(
                name=full_name,
                node_type=NodeType.METHOD,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                source=self._get_node_text(node),
                signature=signature,
                parent=parent,
                dependencies=self._extract_dependencies(node)
            )
            parsed.nodes[full_name] = code_node

    def _extract_variable(self, node, parsed: ParsedCode, parent: Optional[str] = None):
        """Extract variable/const/let declarations (including arrow functions)."""
        for child in node.children:
            if child.type == 'variable_declarator':
                name = None
                is_arrow_fn = False

                for subchild in child.children:
                    if subchild.type == 'identifier':
                        name = self._get_node_text(subchild)
                    elif subchild.type == 'arrow_function':
                        is_arrow_fn = True

                if name and is_arrow_fn:
                    full_name = f"{parent}.{name}" if parent else name
                    code_node = CodeNode(
                        name=full_name,
                        node_type=NodeType.ARROW_FUNCTION,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        source=self._get_node_text(node),
                        signature=f"const {name} = (...) => {{...}}",
                        parent=parent,
                        dependencies=self._extract_dependencies(node)
                    )
                    parsed.nodes[full_name] = code_node

    def _extract_export(self, node, parsed: ParsedCode):
        """Extract export statement."""
        for child in node.children:
            if child.type in ('function_declaration', 'class_declaration'):
                self._walk_tree(child, parsed)
            elif child.type in ('lexical_declaration', 'variable_declaration'):
                self._extract_variable(child, parsed)

    def _extract_params(self, node) -> list[str]:
        """Extract parameter names from formal_parameters node."""
        params = []
        for child in node.children:
            if child.type == 'identifier':
                params.append(self._get_node_text(child))
            elif child.type == 'required_parameter' or child.type == 'optional_parameter':
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        params.append(self._get_node_text(subchild))
                        break
        return params

    def _extract_dependencies(self, node) -> list[str]:
        """Extract identifiers that this node depends on."""
        deps = set()
        self._collect_identifiers(node, deps)
        return list(deps)

    def _collect_identifiers(self, node, deps: set):
        """Recursively collect identifier names."""
        if node.type == 'identifier':
            deps.add(self._get_node_text(node))
        elif node.type == 'call_expression':
            for child in node.children:
                if child.type == 'identifier':
                    deps.add(self._get_node_text(child))
                    break

        for child in node.children:
            self._collect_identifiers(child, deps)

    def _regex_parse(self, parsed: ParsedCode):
        """Fallback regex-based parsing when tree-sitter is not available."""
        # Function declarations
        func_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)'
        for match in re.finditer(func_pattern, self.source):
            name = match.group(1)
            start_line = self.source[:match.start()].count('\n') + 1
            # Find the end of the function (simplified)
            end_line = start_line + 10  # Approximate

            parsed.nodes[name] = CodeNode(
                name=name,
                node_type=NodeType.FUNCTION,
                start_line=start_line,
                end_line=end_line,
                source=match.group(0),
                signature=f"function {name}({match.group(2)})"
            )

        # Arrow functions
        arrow_pattern = r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>'
        for match in re.finditer(arrow_pattern, self.source):
            name = match.group(1)
            start_line = self.source[:match.start()].count('\n') + 1

            parsed.nodes[name] = CodeNode(
                name=name,
                node_type=NodeType.ARROW_FUNCTION,
                start_line=start_line,
                end_line=start_line + 5,
                source=match.group(0),
                signature=f"const {name} = (...) => {{...}}"
            )

        # Classes
        class_pattern = r'(?:export\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, self.source):
            name = match.group(1)
            start_line = self.source[:match.start()].count('\n') + 1

            parsed.nodes[name] = CodeNode(
                name=name,
                node_type=NodeType.CLASS,
                start_line=start_line,
                end_line=start_line + 20,
                source=match.group(0),
                signature=f"class {name}"
            )

        # Imports
        import_pattern = r'import\s+(?:\{([^}]+)\}|(\w+))\s+from'
        for match in re.finditer(import_pattern, self.source):
            if match.group(1):
                imports = [i.strip() for i in match.group(1).split(',')]
                parsed.imports.extend(imports)
            elif match.group(2):
                parsed.imports.append(match.group(2))


def parse_javascript(source: str) -> ParsedCode:
    """Convenience function to parse JavaScript source code."""
    parser = JSParser(source)
    return parser.parse()
