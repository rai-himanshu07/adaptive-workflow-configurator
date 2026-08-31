# Inspector feedback — iteration 8

## Verdict

**FAIL**

Iteration 8 fixes all three iteration-7 state-model failures: status and
transition metadata are authenticated, obsolete lifecycle timing fields are
gone, and live additive state without a verified inverse remains
partial/manual even when signed configuration disables that merge. Normal HMAC
behavior is sound. The key trust boundary is not: an outside key with a
hardlink inside the target is accepted, lets target-local code read the secret,
and can authenticate forged receipt state. Symlinks in ancestor components are
also followed despite the documented no-follow/symlink refusal. In addition,
the test suite creates and depends on the real per-user default key unless its
caller supplies an undocumented environment isolation workaround.

## Scope and method

- Compared the complete result from immutable initial SHA
  `5ca7af1233eee27790ba99f0987c453890a7c3e1` through all eight Builder
  iterations.
- Used all seven prior Inspector reports as mandatory regression lists.
- Read the complete iteration-8 diff and resulting core, typed receipt
  component, CLI, GUI, docs, and focused tests.
- Ran filesystem-heavy checks on project-local tmpfs in an unprivileged
  user/mount namespace, with an isolated `XDG_CONFIG_HOME`.
- Exercised unreadable traversal as mapped EUID 1 and the real visible Tk
  window on `DISPLAY=:0`.

The Builder commit title and trailers are correct. Both required research
documents remain tracked, no dependency manifest changed, and no signing key
or other secret is tracked.

## Blocking findings

### 1. A hardlinked key inside the target defeats the HMAC trust boundary

`_read_signing_key` checks the final path with `lstat`, `O_NOFOLLOW`, `fstat`,
regular-file validation, and owner-only mode validation
(`receipt.py:293-348`). Neither metadata check validates `st_nlink`.

I created the normal protected key outside project A, hardlinked the same inode
as `workspace-secret.key` inside project B, and explicitly applied project B
using the outside pathname. Apply accepted the key:

```text
HARDLINK accepted=True nlink=2
```

Project-local code could then read the 32 secret bytes through the in-target
name. Using only those in-target bytes, I changed the receipt's authenticated
timestamp to 2099, recomputed the corruption checksum and HMAC, and loaded the
receipt through the official outside key:

```text
target_can_resign=2099-01-01T00:00:00.000000000+00:00
```

The HMAC is intended to distinguish editable project state from protected
machine-local authority. Accepting a key inode that is reachable from the
target collapses that distinction, permits authenticated status/timestamp/
inventory forgery, and makes the secret directly stageable in the project.
Normal receipts and output do not expose the key; this accepted alias does.

Require a single-link regular file (`st_nlink == 1`) in both pre-open and
post-open checks and after creation. Refuse a key that gains another link
before use. Add a regression that proves target-visible key bytes cannot sign
a receipt accepted by the outside key.

### 2. No-follow and restrictive-parent handling covers only the final components

Key creation checks only `path.parent.is_symlink()` and opens only the final
basename with `O_NOFOLLOW` (`receipt.py:363-408`). It does not traverse all
components with no-follow directory descriptors or validate an existing
parent's owner/mode.

Observed:

```text
ancestor-link -> real-parent
key path: ancestor-link/nested/receipt.key
ANCESTOR_SYMLINK followed=True mode=0o600
```

The immediate parent (`nested`) was ordinary, so a symlink one component
higher was followed and the key was created. A pre-existing mode-`0777` key
parent was also accepted. The former disproves the documentation's unqualified
claim that symlinked keys refuse, and resolution followed by pathname open
leaves a component-retargeting race that can move creation across the
outside-target boundary.

Walk every key path component with `openat`/directory FDs and no-follow
semantics where supported, and validate existing parent ownership and
writeability before creation/load. If portable standard-library guarantees are
weaker, document the exact boundary rather than claiming general symlink
refusal.

### 3. Focused tests use the ambient per-user signing credential

Most lifecycle tests call `core.apply_project` without `receipt_key_path`, and
the suite does not patch `HOME`, `XDG_CONFIG_HOME`, or the key environment
variable. In a clean isolated `HOME`, running one ordinary existing lifecycle
test created persistent ambient state outside its `TemporaryDirectory`:

```text
TARGETED_TEST_CREATED_AMBIENT_KEY mode=600 bytes=32
```

After changing that ambient key to mode `0644`, rerunning the same otherwise
isolated test failed with:

```text
receipt signing key permissions are insecure ...
```

Thus the required test command can create, consume, and fail because of the
developer's real machine-local credential. The full 78-test suite passed only
because the Inspector explicitly redirected `XDG_CONFIG_HOME` to tmpfs. That
violates the goal's requirement that tests not rely on production data or
credentials.

Patch the key location to each test's temporary root (or a per-test isolated
XDG home) in the test harness. Keep one dedicated default-path test, but run it
under a patched temporary home and assert cleanup/isolation.

## Major iteration-8 successes

### Authenticated receipt state

- Schema 2 HMAC-SHA256 covers canonical complete receipt data, including
  `status` and `rolled_back_at`.
- Status, configuration, timestamp, rendered inventory, and merge tampering
  all failed after recomputing every unkeyed checksum.
- Unsigned and schema-1 receipts failed without project mutation.
- A legitimate rollback transition recomputed both integrity and HMAC.
- Every injected rollback phase restored the exact applied snapshot and
  original signed receipt; retry succeeded and the terminal signature
  verified.
- Post-replace receipt-write recovery remained retryable.

### Ordinary key lifecycle

- Analyze, preview, config/report export, configurator dry-run, GUI read-only
  actions, and legacy no-receipt installation created neither target nor key.
- Explicit apply created one 32-byte key outside the target, mode `0600`; a
  newly created key parent was mode `0700`.
- Missing, wrong, final-symlink, non-regular, insecure-mode, and inside-target
  key paths all refused rollback/apply without project mutation.
- An injected partial key write removed the incomplete key.
- Normal receipts, CLI/GUI output, generated projects, and the tracked tree
  contained no key bytes.

These successes do not cover the hardlink and ancestor-component failures
above.

### Prior state-model failures

- A status-only edit now fails authentication.
- The signed disabled-configuration omitted-merge case returns `partial`,
  lists `.gitignore` in `manual_rendered_paths`, and does not restore it.
- Obsolete `operation_started_ns`, `monotonic_ns`, and `created_at_ns` fields
  are absent rather than permitting incoherent lifecycle claims.
- No-argument rollback still validates all statuses, refuses a newest
  completed receipt without fallback, rejects invalid candidates and exact
  ties, and uses signed wall-clock chronology.

### Deletion-free exact-inverse rollback and UI

- Only verified exact forward/inverse `.gitignore` and settings pairs were
  restored; rendered project files and required directories were never deleted
  or chmodded.
- Forged path, backup, inventory, directory, metadata, duplicate, missing-field,
  and escape cases remained non-authoritative.
- API, CLI, and real GUI continued to report every consistent, missing,
  manual, restored, and required-directory follow-up path.
- Real Tk rows were distinct; preview/diff and both exports were visible;
  protocol guard transitioned auto/on/off in both directions; derived,
  explicit, and imported identity behavior remained correct.

## All prior regression results

| Regression | Iteration-8 result |
|---|---|
| Legacy/configurator dry-run no mutation | **PASS** |
| Analyze/preview/export no target or key mutation | **PASS** |
| Apply failure transactional target cleanup | **PASS** |
| Rollback recovery plus retry for every phase | **PASS** |
| Post-replace receipt-write retry | **PASS** |
| Required directory creation/reapply/preservation | **PASS** |
| No rendered project-file or required-directory deletion | **PASS** |
| Unreadable traversal as mapped EUID 1 | **PASS** |
| Shared CLI/core installer | **PASS** |
| Preset/override/guard behavior | **PASS** |
| Directory/config/proposal/hash/target drift coherence | **PASS** |
| Directory receipt tamper/duplicate/escape/forgery | **PASS safely** |
| Receipt-listed inventory extra/missing/reassignment | **PASS**, refused |
| Exact safe-merge path/backup/forward transform | **PASS** |
| All required receipt fields | **PASS**, actionable/no traceback |
| GUI layout/preview/export/identity/tri-state | **PASS** |
| GUI rollback follow-up path listing | **PASS** |
| Same-second signed chronological selection | **PASS** |
| Invalid candidate / exact signed tie | **PASS**, refused |
| Newest signed rolled-back/partial receipt | **PASS**, refused without fallback |
| Status/config/timestamp/inventory tamper | **PASS**, HMAC refused |
| Unsigned/legacy receipt | **PASS**, refused |
| Unchanged-config omitted merge+backup | **PASS**, partial/manual |
| Disabled-config omitted merge+backup | **PASS**, partial/manual |
| Key final symlink/nonregular/mode/wrong/missing | **PASS**, refused |
| Key hardlink reachable inside target | **FAIL**, accepted and usable to sign |
| Key ancestor symlink / insecure existing parent | **FAIL**, accepted |
| Test isolation from machine key | **FAIL**, ambient key created/consumed |

## Acceptance-criterion verification

1. **PASS — CLI compatibility.** Full legacy tests and independent all-flag
   installation passed: defaults, commands, profiles, every MCP choice,
   sandbox opt-out, security hooks, context settings, additive `.gitignore`,
   collision refusal (`rc=3`), opt-outs, and dry-run.

2. **PASS — shared typed layers.** Core remains argparse/Tkinter-free; adapters
   share its operations; receipt construction, parsing, coherence,
   classification, signing, and transition logic have one owner in
   `receipt.py`.

3. **PASS — configuration model.** Versioned JSON supports every required
   dimension, aliases, and overrides with round-trip and actionable errors.

4. **PASS — import/export/defaults.** External config operations do not create
   a target or signing key, and omitted options preserve personal
   Python/data-science defaults.

5. **PASS — concrete rigor.** Every preset and policy dimension remains
   effective in both override directions, including deliberate guard opt-out.

6. **PASS — deterministic adaptation.** Complexity, scope, testing, and rigor
   deterministically alter the documented low/high-risk policy.

7. **PASS — lean-change contract.** Reuse, non-goals, anti-speculation,
   minimal-surface, and protected-boundary guidance remains present without an
   external framework or universal LOC limit.

8. **PASS — optional GUI controls.** Real Tk rows are distinct and all required
   target, identity, workflow, policy, profile, MCP, command, safety, and
   override controls remain available using only the standard library.

9. **PASS — GUI operations/reporting.** Visible preview/export, confirmation,
   concise status, full rollback lists, identity, tri-state policy, and
   headless smoke all passed.

10. **PASS — structured brownfield analysis.** Manifests/languages,
    environment conflict, uncertain commands, Git/customization/partial state,
    collisions, hazards, directory state, and incomplete scans are represented.

11. **PASS — ordinary no-mutation paths.** Analyze/preview snapshots matched.
    Legacy/configurator dry-run and config/report export wrote no target,
    receipt, key, file, or unrequested output.

12. **PASS — safe apply.** User AGENTS/MCP remained byte-identical; only missing
    files and the two documented additive safe merges were applied with modes
    preserved.

13. **PASS — proposals.** API/CLI/GUI contain intended content, hashes,
    metadata, and diffs; ordinary drift creates coherent current receipts.

14. **FAIL — authentication trust is bypassable.** Complete-payload HMAC fixes
    unkeyed edits only while the key is outside and inaccessible. A detectable
    hardlink inside the target is accepted and gives the target signing
    authority.

15. **FAIL — key-path symlink safety is incomplete.** Project rollback remains
    deletion-free, exact-inverse-only, and transactionally retryable, but the
    new security-critical key path follows ancestor symlinks and accepts
    insecure existing parents despite the required no-follow/restrictive
    boundary.

16. **PASS — idempotency/drift.** Unchanged reapply is a no-op. Missing
    directory, configuration, proposal, target hash, receipt hash, and target
    drift prevent stale reuse and produce coherent current receipts.

17. **PASS — new-project workflow.** New install is complete,
    placeholder-free, doctor-clean, stable on reapply, and deletion-free on
    rollback. Detection remains advisory.

18. **PASS — memory/code-intelligence guidance.** Targeted retrieval, atomic
    checkpoint, supersede, live authority, degraded mode, and optional graph
    capability detection remain correct.

19. **PASS — lifecycle guard.** Core/CLI/GUI guard intent and opt-out work;
    supported events, local-only scope, timeout, and fail-open behavior remain
    truthful.

20. **FAIL — key documentation overstates the boundary.** Ordinary key
    location, HMAC, machine-local rollback, and deletion-free semantics are
    documented. The claim that symlinked/insecure keys refuse is false for
    ancestor symlinks and insecure existing parent directories, and the
    hardlink alias boundary is undisclosed.

21. **FAIL — focused HMAC tests omit boundary aliases.** The 78 passing tests
    cover final symlinks, modes, wrong/missing keys, signatures, unsigned
    receipts, transitions, tamper, and prior regressions. They omit hardlinks,
    ancestor symlink components, insecure existing parents, and ambient-key
    isolation.

22. **FAIL — the test command relies on a machine credential.** The complete
    suite passed in 3.556s on healthy tmpfs only with Inspector-provided
    `XDG_CONFIG_HOME`. Without that override, ordinary tests create/use
    `~/.config/workflow_configurator/receipt-signing.key` and fail according to its
    production state.

23. **PASS with a substantial size caveat — centralization remains clear.** No
    dependency, service, or runtime was added, and signing remains within the
    typed receipt owner. Iteration 8 grew core+receipt from 3,955 to 4,332 lines
    and the single focused test file from 1,326 to 1,628 lines. The next fix
    should replace ad hoc pathname checks with one small, auditable secure-key
    helper rather than add another parallel validation layer.

24. **PASS — preservation.** Both research documents remain tracked; no
    unrelated user or dependency content was removed.

## Quality gates and observed smoke

- `git diff --check 5ca7af1..HEAD` — **PASS**.
- Complete unittest discovery on healthy project-local tmpfs with isolated
  XDG config — **PASS**, 78 tests, 3.556s.
- Generated-project doctor `--strict` — **PASS**, 0 errors/warnings.
- Exact installed placeholder `rg` — **PASS**, no matches.
- Full legacy/configurator flags, import/export, collision, and dry-run —
  **PASS**.
- New/existing analyze/preview/apply/reapply/rollback — **PASS**.
- All ordinary drift, receipt-field, inventory, directory, merge, and fault
  matrices — **PASS**.
- Four signed rollback fault phases plus second retry — **PASS**; transitioned
  signatures verified.
- Newest completed/invalid/tied signed receipt — **PASS**, refused without
  fallback or mutation.
- Unkeyed recomputation of status/config/time/inventory/merge — **PASS**,
  authentication refused.
- Signed disabled-config live additive state — **PASS**, partial/manual.
- Final symlink/nonregular/insecure/wrong/missing/inside-target key — **PASS**,
  refused without target mutation.
- Hardlinked key inside target — **FAIL**, accepted; target re-signed accepted
  state.
- Symlink in a key ancestor — **FAIL**, followed.
- Clean-home ordinary test — **FAIL isolation**, created persistent default key;
  ambient insecure key made the same test fail.
- Real GUI layout, preview/export, tri-state, identity, and all rollback lists —
  **PASS**.
- Direct/CLI headless GUI smoke — **PASS**, 23 actions, 0 errors.
- Unreadable traversal as mapped EUID 1 — **PASS**, actionable diagnostic,
  apply refused with no mutation/key.

## Required next iteration

1. Refuse signing keys with `st_nlink != 1` before and after open/creation, and
   add a target-hardlink authenticated-forgery regression.
2. Resolve/open every key path component with no-follow semantics and validate
   existing key-directory ownership/write permissions; eliminate the
   resolve-then-pathname-open race.
3. Isolate the default key path inside the test harness so the exact test
   command never reads or creates a user's machine credential.
4. Narrow the key documentation to guarantees actually enforced and add
   focused tests for hardlinks, ancestor symlinks, insecure parents, and
   cleanup/race-safe failure.
