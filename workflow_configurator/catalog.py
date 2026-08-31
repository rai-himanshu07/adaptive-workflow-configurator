"""Static, reviewable capability metadata used by every configurator adapter."""

from __future__ import annotations


PROFILE_FILES = {
    "python": (".github/instructions/python.instructions.md",),
    "data-science": (".github/instructions/data-science.instructions.md",),
    "fastapi": (".github/instructions/fastapi.instructions.md",),
    "react": (".github/instructions/react.instructions.md",),
}

LOCAL_CAPABILITY_FILES = {
    "experiment-runner": (
        ".github/skills/experiment-runner/SKILL.md",
        ".github/skills/experiment-runner/scripts/scaffold_experiment.py",
        ".github/skills/experiment-runner/scripts/experiment_tools.py",
        "docs/experiments.md",
    ),
    "specialist-accessibility": (
        ".github/agents/accessibility-reviewer.agent.md",
    ),
    "specialist-tool-evaluator": (
        ".github/agents/tool-evaluator.agent.md",
    ),
    "specialist-appsec": (
        ".github/agents/appsec-reviewer.agent.md",
    ),
    "specialist-research": (
        ".github/agents/research-synthesist.agent.md",
    ),
    "specialist-lean-code": (
        ".github/agents/lean-code-reviewer.agent.md",
    ),
}

MCP_NAMES = ("duckdb", "postgres", "markitdown", "context7", "huggingface")
LOCAL_MCP_NAMES = frozenset({"duckdb", "postgres", "markitdown"})
REVIEWED_MCP_SERVER_NAMES = MCP_NAMES + (
    "mempalace",
    "codebase-memory",
    "codebase-memory-mcp",
    "github",
    "github-mcp-server",
)

OPTIONAL_INTEGRATIONS: dict[str, dict[str, str]] = {
    "rtk": {
        "label": "rtk command compression",
        "kind": "Local tool",
        "summary": "Compress noisy Git, test, build, and shell output before it reaches the model.",
        "guardrail": "Pilot on real commands; output reduction is not the same as total cost reduction.",
    },
    "serena": {
        "label": "Serena symbolic editing",
        "kind": "MCP",
        "summary": "Language-server-backed symbol navigation, rename, and focused editing.",
        "guardrail": "Enable for refactors; keep disabled for research, docs, and simple edits.",
    },
    "jscpd": {
        "label": "jscpd duplication checks",
        "kind": "CLI / MCP",
        "summary": "Detect copied blocks and emit compact, agent-friendly duplication reports.",
        "guardrail": "Prefer the one-shot CLI first; add its MCP server only after measured need.",
    },
    "openspec": {
        "label": "OpenSpec delta specifications",
        "kind": "Workflow skill",
        "summary": "Capture a focused brownfield behavior delta without documenting the whole codebase.",
        "guardrail": "Use for multi-session behavior changes, not routine local fixes.",
    },
    "spec-kit": {
        "label": "GitHub Spec Kit",
        "kind": "Workflow skill",
        "summary": "Use governed specification, plan, task, and implementation artifacts.",
        "guardrail": "Reserve for complex, regulated, or cross-team work; do not combine with OpenSpec.",
    },
    "affected-tests": {
        "label": "Affected-test selection",
        "kind": "Project-native tool",
        "summary": "Run related tests through pytest-testmon, Jest/Vitest changed mode, Nx, Turbo, or Bazel.",
        "guardrail": "Adopt only when the existing test suite is costly; retain broader checkpoint validation.",
    },
    "otel-metadata": {
        "label": "Metadata-only OpenTelemetry",
        "kind": "Observability",
        "summary": "Measure model, token, cache, tool-call, latency, and failure behavior locally.",
        "guardrail": "Do not enable prompt, response, source, or tool-content capture by default.",
    },
    "experiment-runner": {
        "label": "Reproducible experiment runner",
        "kind": "Local workflow skill",
        "summary": "Install the bundled run scaffold and evidence helpers for real ML experimentation.",
        "guardrail": "Select only for projects that run tracked experiments; it adds several substantial local files.",
    },
    "vulture": {
        "label": "Vulture Python dead-code audit",
        "kind": "Optional CLI",
        "summary": "Find high-confidence unused Python code during periodic maintenance.",
        "guardrail": "Dynamic Python creates false positives; never use as an automatic deletion gate.",
    },
    "knip": {
        "label": "Knip JS/TS project audit",
        "kind": "Optional CLI",
        "summary": "Find unused files, exports, and dependencies in an existing JavaScript/TypeScript project.",
        "guardrail": "Use only in projects that already fit Knip's ecosystem and review every result.",
    },
    "semgrep": {
        "label": "Project-specific Semgrep rules",
        "kind": "Optional CLI",
        "summary": "Detect a repeated, proven project-specific overbuilding or safety pattern.",
        "guardrail": "Do not add generic or remote rulesets without a concrete recurring defect.",
    },
    "archify": {
        "label": "Archify milestone diagrams",
        "kind": "Optional documentation tool",
        "summary": "Render a validated typed JSON architecture/workflow artifact for an explicit milestone.",
        "guardrail": "Never run on routine edits; it presents authored understanding and does not analyze code.",
    },
    "specialist-accessibility": {
        "label": "Accessibility reviewer",
        "kind": "Local specialist",
        "summary": "Review user-interface changes against keyboard, semantics, contrast, and assistive-technology needs.",
        "guardrail": "Invoke only for UI work; it reports findings and does not own implementation.",
    },
    "specialist-tool-evaluator": {
        "label": "Tool and dependency evaluator",
        "kind": "Local specialist",
        "summary": "Challenge a proposed dependency or tool against existing capabilities and maintenance cost.",
        "guardrail": "Use when introducing or replacing a dependency, MCP, skill, or service.",
    },
    "specialist-appsec": {
        "label": "AppSec reviewer",
        "kind": "Local specialist",
        "summary": "Review authentication, authorization, secrets, injection, and destructive boundaries.",
        "guardrail": "Invoke only for security-relevant changes; it is not a substitute for normal review.",
    },
    "specialist-research": {
        "label": "Research synthesist",
        "kind": "Local specialist",
        "summary": "Separate verified primary-source facts from inference and operational recommendations.",
        "guardrail": "Use for evidence-heavy research, not ordinary implementation questions.",
    },
    "specialist-lean-code": {
        "label": "Lean-code reviewer",
        "kind": "Local specialist",
        "summary": "Review unexpected files, APIs, dependencies, duplication, and oversized changed functions.",
        "guardrail": "Trigger only when the planned maintenance surface is exceeded; never optimize for LOC alone.",
    },
}

OPTIONAL_INTEGRATION_NAMES = tuple(OPTIONAL_INTEGRATIONS)

SESSION_PROFILES: dict[str, dict[str, str]] = {
    "auto": {
        "label": "Automatic guidance",
        "summary": "Use the project and task policy to recommend a bounded tool set.",
    },
    "quick-docs": {
        "label": "Quick question or docs",
        "summary": "No proactive MCP call; use Context7 only when current external APIs control the answer.",
    },
    "resume-history": {
        "label": "Resume historical work",
        "summary": "Use project-scoped MemPalace; keep unrelated data, model, and document tools off.",
    },
    "large-code": {
        "label": "Large-code investigation",
        "summary": "Use codebase-memory; call MemPalace only when historical decisions matter.",
    },
    "symbol-refactor": {
        "label": "Symbol-heavy refactor",
        "summary": "Use codebase-memory and optionally Serena; keep unrelated MCPs off.",
    },
    "data-analysis": {
        "label": "Data analysis",
        "summary": "Use DuckDB or Postgres and only the project memory needed for interpretation.",
    },
    "document-ingestion": {
        "label": "Document ingestion",
        "summary": "Use MarkItDown and optionally MemPalace; keep code-refactor tools off.",
    },
    "ml-model": {
        "label": "ML/model selection",
        "summary": "Use Hugging Face and Context7; enable data tools only when evidence requires them.",
    },
    "pr-issues": {
        "label": "PR and issue management",
        "summary": "Use GitHub tools; keep local data, document, and model MCPs off.",
    },
}


__all__ = [
    "LOCAL_MCP_NAMES",
    "MCP_NAMES",
    "LOCAL_CAPABILITY_FILES",
    "OPTIONAL_INTEGRATIONS",
    "OPTIONAL_INTEGRATION_NAMES",
    "PROFILE_FILES",
    "SESSION_PROFILES",
]
