# MemPalace Routing and Codebase-Memory Persistence Assessment

**Research date:** 2026-08-30

**Scope:** Actual installed behavior of MemPalace 3.6.0 and
codebase-memory-mcp 0.9.0, with specific attention to project wings, mining,
session writes, index persistence, and freshness.

**Safety:** All inspections and migration commands were read-only. No palace,
project, or code graph was modified.

## Executive Answer

### MemPalace

The current protocol does **not reliably route every completed implementation
to the respective project wing**.

- `mempalace_diary_write(agent_name="copilot")` with no explicit `wing`
  writes to `wing_copilot`.
- `mempalace_diary_read(agent_name="copilot")` with no wing reads recent diary
  entries for that agent **across all wings** in the installed 3.6.0
  implementation.
- `mempalace_checkpoint` requires a wing on each durable drawer item, but its
  optional diary wing defaults to `wing_<agent_name>` when omitted:
  `wing_copilot` when the caller supplies `agent_name="copilot"`.
- The current project template asks for an atomic checkpoint as agent
  `copilot`, but does not require or derive an explicit project wing.

Therefore, project-specific implementation memory lands correctly only when:

1. the agent deliberately supplies a project wing; or
2. a supported MemPalace hook derives a wing from a transcript.

The live palace proves mixed behavior:

- `wing_copilot`: 148 diary drawers, including QC_Tool implementation history;
- `qc_tool`: 7,104 drawers, including mined code/docs/tests and 82 diary
  entries;
- `QC_Tool`: 118 drawers, including 30 diary entries and manually filed
  planning/review/implementation synthesis;
- `CoScriBeRA`: 9 drawers, including two diary entries;
- `adaptive_workflow_configurator`: 48 drawers, including 16 diary entries.

### codebase-memory

codebase-memory **is persistent locally**.

The current `adaptive-workflow-configurator` graph is stored at:

```text
~/.cache/codebase-memory-mcp/adaptive-workflow-configurator.db
```

It survives MCP/CLI process restarts. The current file is approximately 3 MB
and `list_projects`/`index_status` recover it in new CLI invocations.

The `persistence` argument to `index_repository` means something narrower:

```text
persistence=true
```

adds or refreshes the team-shareable repository artifact:

```text
.codebase-memory/graph.db.zst
```

`persistence=false` does **not** make the local index ephemeral. It only avoids
writing that repository artifact.

However, local persistence is not archival durability. The current cache lists
only `adaptive-workflow-configurator`; QC_Tool and CoScriBeRA are not currently indexed there,
even though historical QC_Tool memory mentions an earlier code graph. A cache
cleanup, reinstall, changed cache root, or prior tool version can remove access
to an old local index.

---

# MemPalace Behavior

## 1. Where unscoped writes go

Installed MemPalace 3.6.0 implements diary writes as:

```python
if wing:
    wing = sanitize_name(wing)
else:
    wing = f"wing_{agent_name}"
```

Therefore:

```text
mempalace_diary_write(agent_name="copilot", ...)
```

writes to:

```text
wing_copilot / diary
```

This is an agent-global journal, not a project wing.

The same rule applies to a checkpoint diary when its nested diary object omits
`wing`. If that object also omits `agent_name`, the checkpoint API defaults the
agent to `cursor-ide`, so the diary would land in `wing_cursor-ide`.

## 2. What unscoped reads do

The installed `tool_diary_read` implementation differs from the current MCP
tool-description text.

Actual code:

- always filters `room=diary`;
- always filters `agent=copilot`;
- adds a wing filter only when `wing` is explicitly supplied;
- otherwise returns that agent's recent entries across every wing.

This explains why:

```text
mempalace_diary_read(agent_name="copilot")
```

returned recent `adaptive_workflow_configurator` entries even though the tool schema said an
omitted wing would read `wing_copilot`.

The implementation behavior is more useful than the stale description, but it
also creates cross-project retrieval noise.

## 3. How project-wing writes occur

### Explicit MCP writes

These work correctly when every operation uses the same project wing:

```text
mempalace_search(..., wing="qc_tool")
mempalace_diary_read(agent_name="copilot", wing="qc_tool")
mempalace_checkpoint(
  items=[{"wing": "qc_tool", ...}],
  diary={"agent_name": "copilot", "wing": "qc_tool", ...}
)
```

The recent `adaptive_workflow_configurator` sessions used explicit wing values, which is why the
project wing contains decisions, implementation, verification, research, and
diary entries.

### Supported hooks

MemPalace's Claude Code/Codex hook path derives a project wing from transcript
`cwd` or encoded transcript paths. It produces names such as:

```text
wing_<normalized-project-name>
```

This differs from the project miner's default normalized basename, which
produces names such as:

```text
qc_tool
```

There is no installed hook setting for overriding this derived wing. This can
create another split between `qc_tool` and `wing_qc_tool`.

The current Copilot workflow does not use these MemPalace hooks; it relies on
the agent making MCP calls manually.

## 4. Existing wing fragmentation

The palace currently has multiple aliases for several projects:

- `QC_Tool`
- `qc_tool`
- QC_Tool entries in `wing_copilot`
- `CoScriBeRA`
- a future default mine would normalize that name to `coscribera`
- `DownMan`
- `downman`
- `downman_1.1`

MemPalace's migration dry-run reported:

```text
CoScriBeRA -> coscribera: 9 drawers
DownMan -> downman: 83 drawers (merge)
QC_Tool -> qc_tool: 118 drawers (merge)
```

The command made no changes. It would normalize case/separators but would not
extract project-specific entries from `wing_copilot`.

## 5. What mining does

`mempalace mine PROJECT` indexes project files into semantic drawers and
closets.

For an unchanged file:

- it checks source path and mtime;
- it normally skips re-embedding.

For a modified file:

- it takes a per-file lock;
- deletes every old drawer for that exact `source_file`;
- re-reads and re-chunks the file;
- inserts the current chunks with deterministic IDs;
- replaces the corresponding closet entries.

A shortened file therefore does not leave obsolete high-index chunks.

For a new file:

- new drawers are added.

Mining does **not**:

- infer that an implementation task completed;
- create a project decision or rationale;
- update temporal KG facts;
- remove drawers for files it no longer sees.

That is why mining and session checkpointing are complementary:

- **mine:** searchable source/document content;
- **checkpoint/diary/KG:** durable decisions and session synthesis.

## 6. What sync does

`mempalace sync` is the separate cleanup path. It removes drawers whose source
files are:

- deleted;
- moved;
- now gitignored.

It classifies and reports drawers without source metadata and drawers outside
the selected project roots, but retains them.

The safe update sequence is:

```bash
mempalace sync /path/to/project --wing canonical_wing --dry-run
mempalace sync /path/to/project --wing canonical_wing --apply
mempalace mine /path/to/project --wing canonical_wing
```

The dry run should always be reviewed before the destructive sync.

## 7. Mining versus codebase-memory

Mining an entire source tree into MemPalace overlaps codebase-memory:

- MemPalace provides semantic retrieval over verbatim chunks;
- codebase-memory provides symbols, calls, routes, dependencies, impact, and
  complexity.

When codebase-memory is available, MemPalace should not be treated as the
authoritative live code index. Useful MemPalace mining targets are:

- architecture/decision records;
- plans and accepted design documents;
- operational lessons;
- meeting/research synthesis;
- selected documentation expensive to reconstruct.

Full-source mining remains optional semantic recall, but exact implementation
claims must still use the working tree or code graph.

---

# Current Protocol Gap

The template currently says:

```text
Prefer one atomic mempalace_checkpoint as agent copilot
```

but does not specify:

- canonical project wing;
- how it is derived;
- that every checkpoint item must use it;
- that the nested diary must also use it;
- that reads should be project-scoped by default;
- how mining must use the same wing;
- how legacy aliases are detected.

That omission explains the user's observation.

## Corrected protocol model

Every installed project needs one explicit memory identity:

```yaml
memory:
  wing: qc_tool
  root: /path/to/QC_Tool
```

The wing should be:

- stored in versioned workflow configuration;
- normalized once;
- displayed in the Configurator;
- passed to every project memory read and write;
- passed to mine/sync;
- never guessed independently by each agent.

`wing_copilot` should contain only agent-global information:

- cross-project workflow lessons;
- user preferences;
- general tool behavior;
- reusable agent observations.

It should not receive implementation state for a named project.

## Recommended checkpoint contract

For a substantial project session:

```python
mempalace_checkpoint(
    items=[
        {
            "wing": "qc_tool",
            "room": "decisions",
            "content": "Only durable project decisions."
        }
    ],
    diary={
        "agent_name": "copilot",
        "wing": "qc_tool",
        "topic": "bounded-task",
        "entry": "Concise current session synthesis."
    }
)
```

If there is no valuable drawer synthesis, `items=[]` is valid but the diary
still needs the explicit project wing.

Reads should normally be:

```text
mempalace_diary_read(agent_name="copilot", wing="qc_tool")
mempalace_search(query="...", wing="qc_tool")
```

Use an unscoped cross-wing diary read only when intentionally asking:

> What has this agent worked on recently across projects?

---

# codebase-memory Persistence

## 1. Local database

The installed tool stores all project indexes and configuration under:

```text
~/.cache/codebase-memory-mcp/
```

Current files:

```text
adaptive-workflow-configurator.db       approximately 3 MB
_config.db           approximately 12 KB
```

Each project receives a persistent SQLite database. New CLI processes loaded
the existing project and returned:

```text
nodes: 872
edges: 2,589
status: ready
indexed HEAD: f186715...
```

This proves process-independent local persistence.

## 2. Repository artifact persistence

`index_repository(..., persistence=true)` additionally writes:

```text
.codebase-memory/graph.db.zst
```

This is a compressed graph snapshot for:

- team sharing;
- cache bootstrap after clone;
- avoiding a complete reindex.

It is optional and has repository/merge/storage implications. The default
local SQLite index persists without it.

## 3. Current freshness

The persisted adaptive-workflow-configurator index currently records Git HEAD `f186715`.

`detect_changes` identified three new uncommitted research documents. Therefore:

- the index exists;
- the tool can identify drift;
- the stored graph is not automatically assumed current.

## 4. Auto-index and auto-watch

Current configuration:

```text
auto_index = false
auto_watch = true
auto_index_limit = 50000
```

Meaning:

- a new project is not automatically indexed on session start;
- watching applies to a project after an index exists and while the relevant
  service/session is active;
- changes made while the watcher is absent still require freshness detection
  and incremental reindexing;
- a missing project database is not recreated merely because `auto_watch` is
  true.

## 5. Why old project indexes appear missing

The current cache contains only `adaptive-workflow-configurator`.

QC_Tool memories mention a previous graph with thousands of nodes, but no
current QC_Tool database is present. Likely explanations include:

- the cache was removed;
- the executable/version changed its cache root;
- a prior index used another user/environment;
- the project database was deleted;
- the index was never recreated after setup changes.

Local persistence should therefore be understood as:

> survives normal process/session restarts while the cache remains intact.

It is not:

> a versioned backup that survives cache cleanup, machine changes, or tool
> migration.

---

# Recommended Configurator Improvements

## 1. Project memory identity

Add a `memory_wing` configuration field:

- default: normalized target basename;
- editable before Apply;
- validated against existing wings;
- included in generated workflow guidance;
- used by every generated MemPalace example.

## 2. Wing fragmentation diagnostics

Analyze should detect likely aliases:

- exact case variants;
- hyphen/underscore variants;
- `wing_<project>` variants;
- project-tagged entries in `wing_copilot`.

Show:

- drawer/diary count by alias;
- canonical recommendation;
- migration preview command;
- explicit warning that automatic merging is not performed.

## 3. Correct generated protocol

Generated Planner/Executor/Reviewer/handoff skills should include the exact
project wing in:

- diary read;
- semantic search;
- checkpoint drawer items;
- checkpoint diary;
- mine/sync examples.

Do not rely on `agent_name="copilot"` to imply project routing.

## 4. Separate global and project memory

Define:

- `wing_copilot`: reusable cross-project agent/user/tool knowledge only;
- project wing: decisions, architecture synthesis, milestones, and project
  diary;
- mined code/docs: same project wing, if deliberately enabled;
- KG: cross-project entities and temporal facts, with project-qualified entity
  names when ambiguity exists.

## 5. Memory maintenance workflow

The GUI should offer read-only commands/status:

- palace health;
- project wing counts;
- alias detection;
- last project diary/checkpoint;
- last mine mtime;
- sync dry-run summary.

Actual `sync --apply`, migration, or bulk deletion must require separate
confirmation and should not run as part of normal project Apply.

## 6. Code graph state

Display:

- local index path;
- indexed project name/root;
- indexed Git HEAD;
- node/edge count;
- detected changes;
- auto-index/watch settings;
- whether team artifact export is enabled.

Recommended actions:

- index missing project;
- incrementally refresh stale project;
- optionally enable auto-index;
- optionally export a team artifact after accepting repository implications.

Do not describe `persistence=false` as an ephemeral index.

## 7. Canonical freshness workflow

At session start for a large/unknown code task:

```text
1. Check index_status.
2. Run detect_changes.
3. Incrementally index when changed.
4. Query architecture/symbols/impact.
```

For a small known edit, normal language-service search may remain cheaper.

## Final Recommendation

### MemPalace

Keep it, but fix project identity and routing before adding more memory
features.

Do not assume mining updates decisions. Do not assume an unscoped diary write
uses the project wing. Use explicit canonical wings everywhere.

### codebase-memory

Keep it. It is locally persistent and currently working as designed.

The priority is:

- index each intended project;
- verify freshness;
- decide whether local cache persistence is sufficient;
- use `persistence=true` only when a team-shared repository artifact is
  intentionally wanted.
