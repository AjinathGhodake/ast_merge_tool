"""
Merge Engine Module
Handles the actual merging logic, including LLM integration for conflict resolution.
Uses AWS Bedrock for LLM calls.
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import boto3
from botocore.config import Config

from ast_parser import ParsedCode as PythonParsedCode, parse_code as parse_python
from js_parser import ParsedCode as JSParsedCode, parse_javascript
from ast_differ import DiffResult, ChangeType, compute_diff
from context_extractor import ExtractionResult, MergeContext, extract_context


@dataclass
class MergeDecision:
    """A decision made for a specific change."""
    node_name: str
    action: str  # "keep_base", "keep_target", "merge", "remove"
    merged_code: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "node_name": self.node_name,
            "action": self.action,
            "merged_code": self.merged_code,
            "reason": self.reason,
        }


@dataclass
class MergeResult:
    """Result of the merge operation."""
    success: bool
    merged_code: str
    decisions: list[MergeDecision] = field(default_factory=list)
    conflicts_resolved: int = 0
    auto_merged: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "merged_code": self.merged_code,
            "decisions": [d.to_dict() for d in self.decisions],
            "conflicts_resolved": self.conflicts_resolved,
            "auto_merged": self.auto_merged,
            "error": self.error,
        }


def detect_language(code: str) -> str:
    """Detect the programming language from code content."""
    # Simple heuristics
    js_indicators = [
        'const ', 'let ', 'var ', '=>', 'function(', 'function (',
        'export default', 'export {', 'import {', 'import ', 'require(',
        'module.exports', '===', '!==', 'async function', 'await '
    ]
    py_indicators = [
        'def ', 'class ', 'import ', 'from ', 'self.', '__init__',
        'print(', 'elif ', 'except:', 'try:', 'with ', '    pass'
    ]

    js_score = sum(1 for ind in js_indicators if ind in code)
    py_score = sum(1 for ind in py_indicators if ind in code)

    if js_score > py_score:
        return "javascript"
    return "python"


def parse_code(code: str, language: Optional[str] = None):
    """Parse code based on detected or specified language."""
    if language is None:
        language = detect_language(code)

    if language == "javascript":
        return parse_javascript(code)
    else:
        return parse_python(code)


class BedrockClient:
    """AWS Bedrock client for LLM calls."""

    def __init__(self, region: Optional[str] = None, profile: Optional[str] = None,
                 access_key: Optional[str] = None, secret_key: Optional[str] = None,
                 session_token: Optional[str] = None, model_id: Optional[str] = None,
                 verify_ssl: bool = True):
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.profile = profile or os.getenv("AWS_PROFILE")
        self.access_key = access_key or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.session_token = session_token or os.getenv("AWS_SESSION_TOKEN")
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

        # Debug logging
        print(f"[DEBUG] BedrockClient init:")
        print(f"  Region: {self.region}")
        print(f"  Access Key: {self.access_key[:8] + '...' if self.access_key else 'None'}")
        print(f"  Secret Key: {'***' if self.secret_key else 'None'}")
        print(f"  Session Token: {'***' if self.session_token else 'None'}")
        print(f"  Verify SSL: {verify_ssl}")

        session_kwargs = {'region_name': self.region}
        if self.access_key and self.secret_key:
            session_kwargs['aws_access_key_id'] = self.access_key
            session_kwargs['aws_secret_access_key'] = self.secret_key
            if self.session_token:
                session_kwargs['aws_session_token'] = self.session_token
        elif self.profile:
            session_kwargs['profile_name'] = self.profile

        session = boto3.Session(**session_kwargs)

        config = Config(
            retries={'max_attempts': 3, 'mode': 'standard'}
        )

        self.client = session.client(
            'bedrock-runtime',
            region_name=self.region,
            config=config,
            verify=verify_ssl
        )

    def invoke(self, prompt: str, system_prompt: str = "", max_tokens: int = 2000) -> str:
        """Invoke Claude model via Bedrock."""
        print(f"[DEBUG] Using model: {self.model_id}")

        messages = [{"role": "user", "content": prompt}]

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": 0.1,
        }

        if system_prompt:
            body["system"] = system_prompt

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']


class MergeEngine:
    """Handles code merging with LLM assistance via AWS Bedrock."""

    def __init__(self, base_code: str, target_code: str,
                 language: Optional[str] = None,
                 aws_region: Optional[str] = None,
                 aws_profile: Optional[str] = None,
                 aws_access_key: Optional[str] = None,
                 aws_secret_key: Optional[str] = None,
                 aws_session_token: Optional[str] = None,
                 bedrock_model_id: Optional[str] = None,
                 verify_ssl: bool = True):
        self.base_code = base_code
        self.target_code = target_code
        self.language = language or detect_language(target_code)
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_session_token = aws_session_token
        self.bedrock_model_id = bedrock_model_id
        self.verify_ssl = verify_ssl
        self._bedrock_client = None

    @property
    def bedrock_client(self) -> Optional[BedrockClient]:
        """Lazy initialization of Bedrock client."""
        if self._bedrock_client is None:
            try:
                self._bedrock_client = BedrockClient(
                    region=self.aws_region,
                    profile=self.aws_profile,
                    access_key=self.aws_access_key,
                    secret_key=self.aws_secret_key,
                    session_token=self.aws_session_token,
                    model_id=self.bedrock_model_id,
                    verify_ssl=self.verify_ssl
                )
            except Exception as e:
                print(f"Failed to initialize Bedrock client: {e}")
                return None
        return self._bedrock_client

    def merge(self, strategy: str = "smart") -> MergeResult:
        """
        Perform the merge operation.

        Strategies:
        - "smart": Use LLM for conflicts, auto-merge simple changes
        - "llm_all": Use LLM for all changes
        - "auto": Only auto-merge, skip conflicts
        """
        try:
            # Parse both versions
            base_parsed = parse_code(self.base_code, self.language)
            target_parsed = parse_code(self.target_code, self.language)

            # Compute diff
            diff = compute_diff(base_parsed, target_parsed)

            # Extract context
            extraction = extract_context(base_parsed, target_parsed, diff)

            # Process each change
            decisions = []
            merged_nodes = {}
            conflicts_resolved = 0
            auto_merged = 0

            for context in extraction.contexts:
                change = context.change

                if change.change_type == ChangeType.UNCHANGED:
                    # Keep unchanged nodes
                    node = change.base_node or change.target_node
                    if node:
                        merged_nodes[node.name] = node.source
                        decisions.append(MergeDecision(
                            node_name=node.name,
                            action="keep_base",
                            merged_code=node.source,
                            reason="Unchanged"
                        ))
                    auto_merged += 1

                elif change.change_type == ChangeType.ADDED:
                    # Auto-accept additions
                    node = change.target_node
                    if node:
                        merged_nodes[node.name] = node.source
                        decisions.append(MergeDecision(
                            node_name=node.name,
                            action="keep_target",
                            merged_code=node.source,
                            reason="New addition from target"
                        ))
                    auto_merged += 1

                elif change.change_type == ChangeType.REMOVED:
                    # Handle removals based on strategy
                    if strategy == "auto":
                        # Keep removed in auto mode (conservative)
                        node = change.base_node
                        if node:
                            merged_nodes[node.name] = node.source
                            decisions.append(MergeDecision(
                                node_name=node.name,
                                action="keep_base",
                                merged_code=node.source,
                                reason="Kept (conservative auto mode)"
                            ))
                    else:
                        # Accept removal
                        decisions.append(MergeDecision(
                            node_name=change.name,
                            action="remove",
                            reason="Removed in target"
                        ))
                    auto_merged += 1

                elif change.change_type == ChangeType.MODIFIED:
                    # Handle modifications - this is where LLM helps
                    if strategy == "auto":
                        # In auto mode, keep target version
                        node = change.target_node
                        if node:
                            merged_nodes[node.name] = node.source
                            decisions.append(MergeDecision(
                                node_name=node.name,
                                action="keep_target",
                                merged_code=node.source,
                                reason="Auto-merged (kept target)"
                            ))
                        auto_merged += 1
                    elif self.bedrock_client and strategy in ("smart", "llm_all"):
                        # Use Bedrock LLM to merge
                        merged = self._llm_merge(context)
                        merged_nodes[change.name] = merged.merged_code
                        decisions.append(merged)
                        conflicts_resolved += 1
                    else:
                        # No LLM available, keep target
                        node = change.target_node
                        if node:
                            merged_nodes[node.name] = node.source
                            decisions.append(MergeDecision(
                                node_name=node.name,
                                action="keep_target",
                                merged_code=node.source,
                                reason="No LLM available, kept target"
                            ))
                        auto_merged += 1

            # Reconstruct the merged code
            merged_code = self._reconstruct_code(
                base_parsed, target_parsed, merged_nodes, decisions
            )

            return MergeResult(
                success=True,
                merged_code=merged_code,
                decisions=decisions,
                conflicts_resolved=conflicts_resolved,
                auto_merged=auto_merged
            )

        except Exception as e:
            import traceback
            return MergeResult(
                success=False,
                merged_code="",
                error=f"{str(e)}\n{traceback.format_exc()}"
            )

    def _llm_merge(self, context: MergeContext) -> MergeDecision:
        """Use Bedrock LLM to merge a conflicting change."""
        lang_hint = "JavaScript/TypeScript" if self.language == "javascript" else "Python"

        prompt = f"""You are a code merge assistant for {lang_hint}. Analyze the following code change and produce the best merged version.

{context.to_prompt_context()}

Instructions:
1. If both versions have valid changes, combine them intelligently
2. Preserve the intent of both versions where possible
3. Maintain code style consistency
4. Return ONLY the merged code, no explanations or markdown fences

Respond with the merged code:"""

        system_prompt = f"You are a precise {lang_hint} code merge assistant. Return only code, no markdown fences, no explanations, no commentary."

        try:
            merged_code = self.bedrock_client.invoke(prompt, system_prompt)

            # Clean up any markdown code fences
            merged_code = re.sub(r'^```\w*\n?', '', merged_code.strip())
            merged_code = re.sub(r'\n?```$', '', merged_code)

            return MergeDecision(
                node_name=context.change.name,
                action="merge",
                merged_code=merged_code,
                reason="Bedrock LLM-assisted merge"
            )

        except Exception as e:
            # Fallback to target version
            node = context.change.target_node
            return MergeDecision(
                node_name=context.change.name,
                action="keep_target",
                merged_code=node.source if node else "",
                reason=f"Bedrock error, kept target: {str(e)}"
            )

    def _reconstruct_code(self, base, target, merged_nodes: dict,
                          decisions: list[MergeDecision]) -> str:
        """Reconstruct the full merged code."""
        # Start with target as the base structure
        lines = self.target_code.split('\n')

        # Build a map of what to replace
        replacements = []

        # Get all nodes from target for positioning
        all_target_nodes = sorted(
            target.nodes.values(),
            key=lambda n: n.start_line
        )

        # Track which lines are covered by nodes
        covered_lines = set()
        for node in all_target_nodes:
            for line in range(node.start_line, node.end_line + 1):
                covered_lines.add(line)

        # For modified nodes, we need to replace the target version
        for decision in decisions:
            if decision.action == "merge" and decision.merged_code:
                # Find the node in target
                if decision.node_name in target.nodes:
                    node = target.nodes[decision.node_name]
                    replacements.append({
                        'start': node.start_line - 1,
                        'end': node.end_line,
                        'code': decision.merged_code
                    })

        # Apply replacements in reverse order to preserve line numbers
        replacements.sort(key=lambda r: r['start'], reverse=True)

        for rep in replacements:
            lines[rep['start']:rep['end']] = rep['code'].split('\n')

        return '\n'.join(lines)


def merge_code(base_code: str, target_code: str,
               strategy: str = "smart",
               language: Optional[str] = None,
               aws_region: Optional[str] = None,
               aws_profile: Optional[str] = None,
               aws_access_key: Optional[str] = None,
               aws_secret_key: Optional[str] = None,
               aws_session_token: Optional[str] = None,
               bedrock_model_id: Optional[str] = None,
               verify_ssl: bool = True) -> MergeResult:
    """Convenience function to merge code."""
    engine = MergeEngine(
        base_code, target_code,
        language=language,
        aws_region=aws_region,
        aws_profile=aws_profile,
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
        aws_session_token=aws_session_token,
        bedrock_model_id=bedrock_model_id,
        verify_ssl=verify_ssl
    )
    return engine.merge(strategy)
