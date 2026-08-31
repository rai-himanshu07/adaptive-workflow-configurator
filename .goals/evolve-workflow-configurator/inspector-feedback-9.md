# Inspector feedback — iteration 9

## Verdict

**FAIL**

Iteration 9 fixes the stable-state key defects from iteration 8: the exact
unittest command no longer touches the ambient per-user key, pre-existing and
post-open hardlinks are refused before later HMAC use, every tested ancestor
symlink is refused, parent owner/mode policy is enforced, actual filesystem
identity prevents explicit/default aliases into the target, and ordinary
signed apply/transition/retry still works.

The secure helper is not transactional across validation and use, however. A
hardlink added **after** `validate_live()` but inside `hmac.new()` is accepted,
leaves the complete key readable inside the target, and still writes a signed
receipt. Moving the held key-directory component into the target during the
same interval is also accepted and signs successfully with the key now inside
the target. Short-lived hardlinks/component moves can copy the secret and be
removed before the next validation, leaving no detectable `st_nlink` or
identity change. Partial-create failures also leak descriptors, and a
hardlink introduced after the first partial byte prevents cleanup of both the
external partial key and its target alias.

## Scope and method

- Compared the complete result from immutable initial SHA
  `5ca7af1233eee27790ba99f0987c453890a7c3e1` through all nine Builder
  iterations.
- Used all eight prior Inspector reports as mandatory regression lists.
- Read the iteration-9 diff and resulting core, 1,847-line receipt component,
  CLI, GUI, documentation, and 1,832-line focused test module.
- Ran the exact test command with ordinary ambient `HOME`/unset
  `XDG_CONFIG_HOME`, then ran it again in a healthy isolated tmpfs chroot.
- Exercised real Tk on `DISPLAY=:0`, both headless entry points, generated
  doctor/placeholders, complete legacy/new/existing CLI workflows, and
  unreadable traversal as mapped EUID 1.
- Ran independent signed receipt, latest-state, tamper, exact-merge,
  deletion-free, and rollback-fault matrices.
- Ran key-path adversarial tests in a root-owned, mode-`0755` tmpfs chroot so
  the documented POSIX ancestor policy was meaningful and not hidden by the
  repository's group-writable NTFS mount.

The Builder commit title and trailers are correct. Both required research
documents remain tracked, no dependency manifest changed, and no key or secret
is tracked.

## Blocking findings

### 1. Link and component checks are not atomic with HMAC use

`sign()` calls `SigningKey.validate_live()` and then separately calls
`hmac.new()` (`receipt.py:247-256`). `validate_live()` confirms the current key
`st_nlink`, key path identity, retained directory descriptors, live directory
entries, and target chain (`receipt.py:129-170`), but releases control before
the actual HMAC computation.

I injected a deterministic filesystem action from the first `hmac.new()` call:

1. Load a valid single-link key outside an existing target.
2. `validate_live()` passes.
3. Inside `hmac.new()`, hardlink the key into the target.
4. Continue the real HMAC call.

Observed:

```text
HARDLINK_DURING_HMAC accepted
nlink 2
secret_in_target True
receipt_written True
```

The explicit apply completed and wrote an authenticated receipt while the
complete 32-byte secret was available as `workspace-secret.key` inside the
target.

The same validation/use gap exists for path identity. I moved the held
outside key parent into the target and recreated an empty directory at the old
pathname from inside `hmac.new()`:

```text
COMPONENT_DURING_HMAC accepted
key_now_in_target True
receipt_written True
```

This directly contradicts the documented statement that link/identity checks
are repeated “before each HMAC use” as a sufficient boundary. They happen
before the use, but are not bound to it and have no post-use check. At minimum,
validate immediately before **and after** every HMAC computation and fail the
whole transaction if either check fails. Prefer an API which owns validation,
HMAC, and final validation as one auditable operation rather than exposing
`SigningKey` as a `bytes` subclass.

### 2. Transient aliases permanently disclose the key without leaving evidence

Even validation before and after later operations cannot prove that the secret
was never exposed. Starting from a loaded valid key, I created a target
hardlink, copied its bytes into a normal target file, removed the hardlink, and
then called `validate_live()` plus `sign()`:

```text
TRANSIENT_HARDLINK accepted
nlink_restored 1
target_retains_key_copy True
```

I also temporarily moved the held key parent into the target, copied the key,
moved the parent back to its original pathname, and then validated:

```text
TRANSIENT_COMPONENT_MOVE accepted
target_retains_key_copy True
```

All stable identities and link counts were restored, so the helper cannot
detect either disclosure. This is a fundamental limit of a pathname-owned key
that remains hardlinkable/movable by the same actor. Documentation currently
describes stronger protection than the helper can prove.

If the intended threat boundary excludes concurrent same-UID filesystem
actors, state that explicitly and do not claim that held descriptors prevent a
key path entering the target. If same-UID target code is in scope, use a
non-exportable OS key facility or another boundary which cannot be copied via a
brief filesystem alias; repeated `st_nlink` checks alone cannot establish that
property.

### 3. Partial key creation leaks descriptors and can leave a partial secret

The ordinary injected-write test passes its filesystem assertions: the key and
new leaf directory disappear. `_create_key`, however, does not close its
descriptor in either `ReceiptError` or general `OSError` paths
(`receipt.py:734-751`), and `_open_signing_key` never receives the still-local
descriptor to close.

Repeating a simple first-write failure 24 times produced:

```text
PARTIAL_CREATE filesystem_clean True fd_delta 10
```

The delta stopped at 10 only because older traceback/exception objects were
collected during the loop; failures still retain descriptors until GC rather
than closing deterministically.

A stronger injected fault wrote one byte, hardlinked the just-created key into
the target, and then raised. Cleanup deliberately unlinks only when
`st_nlink == 1`, so both names and the descriptor remain:

```text
PARTIAL_HARDLINK external_left True
target_alias_left True
size 1
nlink 2
```

This violates the requested partial-key cleanup. Always close the local
descriptor on every `_create_key` exit. For a file this call created with
`O_EXCL`, remove the exact directory entry by identity on failure regardless of
an added link; separately report that an external alias may remain rather than
silently leaving both partial entries.

## Iteration-8 failure retest

| Iteration-8 failure | Iteration-9 result |
|---|---|
| Test suite creates/uses ambient key | **Fixed.** Exact command passed with ambient key device/inode/mode/size/link/atime/mtime/ctime unchanged. |
| Existing target hardlink before apply | **Fixed.** Refused before metadata/project writes. |
| Hardlink added after key open, before later HMAC | **Fixed for stable link.** `validate_live()` refused. |
| Hardlink added after final validation during HMAC | **FAIL.** Apply and receipt signing succeeded with secret in target. |
| Transient hardlink added/copied/removed | **FAIL.** Subsequent validation accepted; copied secret remained. |
| Ancestor symlink at shallow/deep depth | **Fixed.** Both refused using directory-FD traversal. |
| Insecure `0777` parent | **Fixed.** Refused. |
| Wrong-owner parent | **Fixed.** Refused under a meaningful UID map. |
| Immediate component replacement after load | **Fixed.** `validate_live()` refused. |
| Component moved into target during HMAC | **FAIL.** Apply signed successfully with actual key inside target. |
| Explicit/default path aliasing target by actual identity | **Fixed.** Bind-mounted alias refused before key/directory creation. |
| Ordinary partial first-write failure | **Filesystem fixed, descriptor leak remains.** |
| Partial write plus hardlink | **FAIL.** One-byte two-link partial key remained. |

## Major successes

### Exact suite and ambient credential isolation

- `python -m unittest discover -s workflow_configurator/tests -v` passed all 76 tests in
  4.524s using ordinary `HOME` and unset `XDG_CONFIG_HOME`.
- The ambient key's device, inode, mode, owner, link count, size, atime, mtime,
  and ctime were identical before and after.
- The same 76 tests passed in 7.689s in a healthy tmpfs chroot.
- The test base class redirects every ordinary apply to an isolated protected
  per-case key. The one default-path test patches both home and XDG explicitly.

### Stable key-path policy

- Valid explicit/default keys are outside the target, 32 bytes, mode `0600`,
  single-link, and use a mode-`0700` tool-created leaf.
- Final and ancestor symlinks, non-directories, insecure mode, unexpected
  owners, wrong keys, missing keys, non-regular keys, and stable hardlinks are
  refused.
- Every absolute key directory is opened using retained `dir_fd`,
  `O_DIRECTORY`, and `O_NOFOLLOW`; unsupported primitives fail closed.
- Stable component replacement and bind-mounted actual target identity are
  detected without `Path.resolve()` reopening the key.
- Ordinary key bytes and key paths do not appear in receipts, generated
  projects, CLI/GUI output, or tracked files.

These stable checks are real improvements, but do not close findings 1–3.

### Receipt and rollback behavior

- Recomputed unkeyed status/config/timestamp/inventory changes, unsigned
  receipts, legacy receipts, and wrong signatures all refused without project
  mutation.
- No-argument selection chose the newest signed receipt across statuses, then
  refused newest completed state without fallback. Signed ties and invalid
  candidates refused without fallback/mutation.
- Live additive state without an authenticated inverse returned
  `partial/manual`, including signed configuration which disables the merge.
- Signed reassignment of merge state to a user README refused.
- Valid rollback restored exactly `.gitignore` and settings, preserved modes,
  all rendered files, user files, and required-directory identity/mode.
- Every compatibility fault phase restored the signed applied snapshot and a
  second rollback succeeded.

### Workflow and UI regressions

- Full legacy flags, collision refusal, dry-run, opt-outs, all MCP choices,
  hooks, and context settings passed; legacy paths created no receipt key.
- Config export, preview, analysis, and apply+dry-run were non-mutating and did
  not create/read/change the signing key.
- New apply/reapply/rollback, generated strict doctor, and exact installed
  placeholder scan passed.
- Existing analyze/preview/apply/reapply/rollback preserved user AGENTS/MCP,
  surfaced Conda+uv and proposals, applied only the two safe merges, and
  restored them exactly.
- EUID-1 unreadable traversal produced
  `traversal.permission-denied`, blocked apply, and created no key.
- Real Tk rows, proposal/content/diff, exports, confirmation, rollback lists,
  guard auto/on/off, and derived/explicit/imported identity passed.
- Both direct and CLI-routed headless GUI smoke passed without target/key
  mutation.

## Acceptance-criterion verification

1. **PASS — CLI compatibility.** Existing flags, defaults, profiles, all MCP
   choices, commands, collision refusal, legacy dry-run, safety options, and
   opt-outs passed independently and in the complete suite.

2. **PASS — shared typed layers.** Core remains argparse/Tkinter-free and CLI/GUI
   remain adapters over shared operations. Receipt state and key handling have
   one product-code owner, though criterion 23 records its size.

3. **PASS — configuration model.** Versioned round-trip and actionable
   validation continue to cover all required dimensions and overrides.

4. **PASS — import/export/defaults.** External configuration operations neither
   modify the target nor touch the key; omitted options preserve personal
   Python/data-science defaults.

5. **PASS — concrete rigor.** All named presets and policy dimensions remain
   effective in both override directions, including deliberate guard opt-out.

6. **PASS — deterministic adaptation.** Complexity, scope, testing, and rigor
   continue to produce the documented low/high-risk policy.

7. **PASS — lean-change contract.** Required reuse, non-goals,
   anti-speculation, minimal surface, and protected-boundary guidance remains
   without external frameworks or universal LOC rules.

8. **PASS — optional GUI controls.** The real standard-library Tk window exposes
   all required controls in distinct rows.

9. **PASS — GUI operations/reporting.** Visible preview/export, confirmations,
   concise status, complete follow-up lists, identity, tri-state policy, and
   both headless paths passed.

10. **PASS — structured brownfield analysis.** Required facts, collisions,
    proposals, hazards, directory state, and incomplete scans remain
    structured.

11. **PASS — ordinary no-mutation paths.** Analyze, preview, export, and both
    dry-run modes preserve complete targets and do not create/read/change a
    key.

12. **PASS — safe apply.** User AGENTS/MCP remain byte-identical; only missing
    files and documented additive `.gitignore`/settings merges are applied
    with modes preserved.

13. **PASS — proposals.** API/CLI/GUI expose intended content, hashes, metadata,
    and diffs while originals remain unchanged.

14. **FAIL — authenticated authority can still escape into the target.** Stable
    HMAC tamper/state checks pass, but a link or component move during HMAC
    exposes the key and still authorizes the receipt.

15. **FAIL — key creation/use is not fully transactional.** Ordinary apply and
    rollback fault recovery pass. The HMAC validation/use races and partial-key
    descriptor/filesystem cleanup failures violate the new critical safety
    boundary.

16. **PASS — idempotency/drift.** Reapply and repeated preview remain stable;
    missing directory, config, proposal, target hash, receipt hash, and target
    drift still prevent stale reuse.

17. **PASS — new-project workflow.** New install is complete,
    placeholder-free, doctor-clean, stable on reapply, and deletion-free on
    rollback.

18. **PASS — memory/code-intelligence guidance.** Targeted retrieval, atomic
    checkpoint, supersede, live authority, degraded mode, and optional graph
    capability detection remain correct.

19. **PASS — lifecycle guard.** Core/CLI/GUI intent and opt-out work; supported
    events, local-only scope, timeout, and fail-open behavior remain truthful.

20. **FAIL — documentation exceeds the enforceable platform boundary.** It
    accurately documents POSIX descriptor primitives, ownership/mode policy,
    ACL limitations, and fail-closed unsupported platforms. It says held
    directory identity prevents a key path entering the target and that
    link/identity checks protect each HMAC use; findings 1–2 disprove that under
    concurrent/transient same-UID filesystem actions. This threat limitation is
    not documented.

21. **FAIL — focused security coverage remains incomplete.** The 76 passing
    tests cover stable hardlinks, two ancestor symlink depths, parent policy,
    one component replacement, ordinary partial write cleanup, default-key
    isolation, and all prior receipt cases. They omit the validation/HMAC
    interval, transient alias history, directory move into target during HMAC,
    descriptor leak assertion, and partial-write-plus-hardlink cleanup.

22. **PASS — complete quality gates/workflows.** Exact and healthy-tmpfs suites
    passed with no ambient credential mutation. New/existing/legacy, generated
    doctor/placeholders, real/headless GUI, and unreadable traversal produced
    observed passing output without network or display-dependent tests.

23. **FAIL — separation is now warranted.** No dependency/service/runtime was
    added and the code is standard-library-only. However, `receipt.py` grew
    from 1,411 to 1,847 lines and now combines a 101-line resource-owning key
    class, roughly 500 lines of POSIX descriptor/path/key lifecycle, a
    176-line schema validator, receipt construction/selection/coherence,
    rendered inventory, merge proof, and rollback classification. It also
    lazily calls private core functions in dozens of places. The missed close paths
    and validation/use race demonstrate that this is no longer manageable
    enough as one component. A focused internal key-store module with explicit
    context-manager lifetime and a narrow sign/verify API would materially
    improve understanding without adding a framework.

24. **PASS — preservation.** Both research documents remain tracked; no
    unrelated user/dependency content was removed.

## Quality gates and observed smoke

- `git diff --check 5ca7af1..HEAD` — **PASS**.
- Exact unittest discovery, ordinary ambient home/XDG — **PASS**, 76 tests,
  4.524s; ambient key metadata unchanged.
- Complete unittest discovery in healthy tmpfs chroot — **PASS**, 76 tests,
  7.689s.
- Generated-project doctor `--strict` — **PASS**, 0 errors/warnings.
- Exact installed placeholder `rg` — **PASS**, no matches.
- Full legacy/configurator flags and new/existing workflows — **PASS**.
- Independent HMAC/tamper/latest/partial/exact-merge/deletion-free/fault matrix
  — **PASS**.
- Stable hardlink before open and after open/before later use — **PASS**,
  refused.
- Ancestor symlinks, insecure parent, wrong-owner parent, and actual-identity
  target alias — **PASS**, refused.
- Hardlink added inside `hmac.new()` — **FAIL**, apply signed and exposed key.
- Parent moved into target inside `hmac.new()` — **FAIL**, apply signed with key
  now inside target.
- Transient hardlink/component move followed by copy and restoration — **FAIL**,
  later validation accepted while copied key remained.
- Repeated partial first-write fault — **FAIL resource cleanup**, filesystem
  clean but descriptors retained until GC.
- Partial write plus hardlink — **FAIL filesystem cleanup**, both one-byte
  entries remained.
- Real Tk and direct/CLI headless smoke — **PASS**.
- Unreadable traversal as EUID 1 — **PASS**, actionable/no mutation/key.

## Required next iteration

1. Make secure-key lifetime explicit with deterministic close on every success
   and failure path; add FD-count regressions around repeated create/open faults.
2. Bind validation and HMAC in one helper and validate both immediately before
   and after use; an after-use failure must abort/restore the apply or rollback
   transaction.
3. Clean the exact `O_EXCL`-created directory entry on partial-write failure
   even if a concurrent hardlink appears, and report unavoidable aliases
   explicitly.
4. Decide and document whether concurrent same-UID actors are outside the
   threat model. If they are in scope, filesystem link-count/path checks cannot
   prove non-disclosure; use a non-exportable key boundary.
5. Separate the POSIX key-store/resource lifecycle from receipt schema/state and
   expose only a small context-managed sign/verify interface.
