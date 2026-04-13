"""
AST Differ Module
Compares two parsed ASTs and identifies structural differences.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ast_parser import ParsedCode, CodeNode


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class NodeChange:
    """Represents a change to a code node."""
    name: str
    change_type: ChangeType
    base_node: Optional[CodeNode] = None
    target_node: Optional[CodeNode] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "change_type": self.change_type.value,
            "base_node": self.base_node.to_dict() if self.base_node else None,
            "target_node": self.target_node.to_dict() if self.target_node else None,
        }


@dataclass
class DiffResult:
    """Container for diff results."""
    changes: list[NodeChange]
    added_count: int = 0
    removed_count: int = 0
    modified_count: int = 0
    unchanged_count: int = 0

    def to_dict(self) -> dict:
        return {
            "changes": [c.to_dict() for c in self.changes],
            "added_count": self.added_count,
            "removed_count": self.removed_count,
            "modified_count": self.modified_count,
            "unchanged_count": self.unchanged_count,
            "summary": {
                "total_changes": self.added_count + self.removed_count + self.modified_count,
                "has_conflicts": self.modified_count > 0,
            }
        }


class ASTDiffer:
    """Compares two ParsedCode structures and identifies differences."""

    def __init__(self, base: ParsedCode, target: ParsedCode):
        self.base = base
        self.target = target

    def diff(self) -> DiffResult:
        """Compute the difference between base and target."""
        changes = []
        added = 0
        removed = 0
        modified = 0
        unchanged = 0

        base_names = set(self.base.nodes.keys())
        target_names = set(self.target.nodes.keys())

        # Find added nodes (in target but not in base)
        for name in target_names - base_names:
            changes.append(NodeChange(
                name=name,
                change_type=ChangeType.ADDED,
                target_node=self.target.nodes[name]
            ))
            added += 1

        # Find removed nodes (in base but not in target)
        for name in base_names - target_names:
            changes.append(NodeChange(
                name=name,
                change_type=ChangeType.REMOVED,
                base_node=self.base.nodes[name]
            ))
            removed += 1

        # Find modified/unchanged nodes (in both)
        for name in base_names & target_names:
            base_node = self.base.nodes[name]
            target_node = self.target.nodes[name]

            if self._nodes_equal(base_node, target_node):
                changes.append(NodeChange(
                    name=name,
                    change_type=ChangeType.UNCHANGED,
                    base_node=base_node,
                    target_node=target_node
                ))
                unchanged += 1
            else:
                changes.append(NodeChange(
                    name=name,
                    change_type=ChangeType.MODIFIED,
                    base_node=base_node,
                    target_node=target_node
                ))
                modified += 1

        # Sort changes: modified first, then added, then removed, then unchanged
        priority = {
            ChangeType.MODIFIED: 0,
            ChangeType.ADDED: 1,
            ChangeType.REMOVED: 2,
            ChangeType.UNCHANGED: 3
        }
        changes.sort(key=lambda c: (priority[c.change_type], c.name))

        return DiffResult(
            changes=changes,
            added_count=added,
            removed_count=removed,
            modified_count=modified,
            unchanged_count=unchanged
        )

    def _nodes_equal(self, node1: CodeNode, node2: CodeNode) -> bool:
        """Check if two nodes are semantically equal."""
        # Normalize whitespace for comparison
        source1 = self._normalize_source(node1.source)
        source2 = self._normalize_source(node2.source)
        return source1 == source2

    def _normalize_source(self, source: str) -> str:
        """Normalize source code for comparison."""
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in source.strip().split('\n')]
        # Remove empty lines
        lines = [line for line in lines if line]
        return '\n'.join(lines)


def compute_diff(base: ParsedCode, target: ParsedCode) -> DiffResult:
    """Convenience function to compute diff."""
    differ = ASTDiffer(base, target)
    return differ.diff()
