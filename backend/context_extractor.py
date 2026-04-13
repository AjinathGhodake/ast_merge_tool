"""
Context Extractor Module
Extracts minimal context needed for LLM to understand and merge code changes.
"""

from dataclasses import dataclass, field

from ast_parser import ParsedCode, CodeNode, NodeType
from ast_differ import DiffResult, NodeChange, ChangeType


@dataclass
class MergeContext:
    """Context needed for merging a specific change."""
    change: NodeChange
    related_nodes: list[CodeNode] = field(default_factory=list)
    import_context: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "change": self.change.to_dict(),
            "related_nodes": [n.to_dict() for n in self.related_nodes],
            "import_context": self.import_context,
        }

    def to_prompt_context(self) -> str:
        """Generate a concise context string for LLM prompt."""
        parts = []

        # Add imports if relevant
        if self.import_context:
            parts.append("# Relevant imports:")
            parts.append('\n'.join(f"# - {imp}" for imp in self.import_context[:10]))
            parts.append("")

        # Add related code context
        if self.related_nodes:
            parts.append("# Related code context:")
            for node in self.related_nodes[:5]:  # Limit to 5 related nodes
                parts.append(f"# {node.node_type.value}: {node.name}")
                parts.append(f"# Signature: {node.signature}")
                parts.append("")

        # Add the actual change
        change = self.change
        if change.change_type == ChangeType.MODIFIED:
            parts.append("# === BASE VERSION ===")
            parts.append(change.base_node.source if change.base_node else "")
            parts.append("")
            parts.append("# === TARGET VERSION ===")
            parts.append(change.target_node.source if change.target_node else "")
        elif change.change_type == ChangeType.ADDED:
            parts.append("# === NEW CODE TO ADD ===")
            parts.append(change.target_node.source if change.target_node else "")
        elif change.change_type == ChangeType.REMOVED:
            parts.append("# === CODE TO REMOVE ===")
            parts.append(change.base_node.source if change.base_node else "")

        return '\n'.join(parts)


@dataclass
class ExtractionResult:
    """Result of context extraction."""
    contexts: list[MergeContext]
    total_tokens_estimate: int = 0

    def to_dict(self) -> dict:
        return {
            "contexts": [c.to_dict() for c in self.contexts],
            "total_tokens_estimate": self.total_tokens_estimate,
            "context_count": len(self.contexts),
        }


class ContextExtractor:
    """Extracts minimal context for LLM merging."""

    def __init__(self, base: ParsedCode, target: ParsedCode, diff: DiffResult):
        self.base = base
        self.target = target
        self.diff = diff

    def extract(self, include_unchanged: bool = False) -> ExtractionResult:
        """Extract context for all changes."""
        contexts = []
        total_chars = 0

        for change in self.diff.changes:
            if change.change_type == ChangeType.UNCHANGED and not include_unchanged:
                continue

            context = self._extract_for_change(change)
            contexts.append(context)
            total_chars += len(context.to_prompt_context())

        # Rough token estimate (4 chars per token)
        token_estimate = total_chars // 4

        return ExtractionResult(
            contexts=contexts,
            total_tokens_estimate=token_estimate
        )

    def _extract_for_change(self, change: NodeChange) -> MergeContext:
        """Extract context for a single change."""
        related_nodes = []
        import_context = []

        # Get the node we're working with
        node = change.target_node or change.base_node
        if not node:
            return MergeContext(change=change)

        # Find dependencies
        deps = set(node.dependencies)

        # If it's a method, include the class context
        if node.parent:
            if node.parent in self.base.nodes:
                parent_node = self.base.nodes[node.parent]
                # Add just the signature, not full source
                related_nodes.append(CodeNode(
                    name=parent_node.name,
                    node_type=parent_node.node_type,
                    start_line=parent_node.start_line,
                    end_line=parent_node.start_line,
                    source=parent_node.signature,
                    signature=parent_node.signature
                ))

        # Find related nodes that this code depends on
        all_nodes = {**self.base.nodes, **self.target.nodes}
        for dep_name in deps:
            # Check if any node matches this dependency
            for node_name, dep_node in all_nodes.items():
                if node_name == dep_name or node_name.endswith(f".{dep_name}"):
                    if dep_node.name != node.name:  # Don't include self
                        related_nodes.append(dep_node)
                        break

        # Extract relevant imports
        all_imports = list(set(self.base.imports + self.target.imports))
        for imp in all_imports:
            # Check if import is used by this node
            imp_name = imp.split('.')[-1]
            if imp_name in deps:
                import_context.append(imp)

        return MergeContext(
            change=change,
            related_nodes=related_nodes[:5],  # Limit context size
            import_context=import_context[:10]
        )


def extract_context(base: ParsedCode, target: ParsedCode, diff: DiffResult) -> ExtractionResult:
    """Convenience function to extract context."""
    extractor = ContextExtractor(base, target, diff)
    return extractor.extract()
