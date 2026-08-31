# MemPalace Session Lock Contention Assessment

**Assessment date:** 2026-08-30

**Installed version:** MemPalace 3.6.0

**Scope:** Why an active Copilot session prevents a separate
`mempalace mine`, what is holding the current palace, safe immediate
workarounds, and whether newer MemPalace architecture resolves it.

**Safety:** Inspection was read-only. No process was stopped, no lock file was
removed, no package was upgraded, and no palace write was attempted from a
second process.

## Executive Answer

The observation is correct. In the current MemPalace 3.6.0 topology, the first
writable MCP process to perform a mutation takes a palace-wide writer lease and
holds it until that process exits.

This Copilot session is currently that process:

```text
PID 883093
<python> -m mempalace.mcp_server
parent: GitHub Copilot CLI runtime
```

It holds:

```text
~/.mempalace/locks/mine_palace_5041d50551d021ce.lock
```

`lsof` and a non-blocking `flock` probe both confirmed the lease is active.

A separate CLI miner needs the same lease. Consequently, a real:

```bash
mempalace mine /path/to/project
```

is refused while the session process remains alive.

The lock is protecting Chroma/FTS/HNSW from concurrent long-lived clients. It
is not safe to bypass casually.

## What Is and Is Not Causing It

### The current session is the holder

The writable stdio MCP process was started with this Copilot runtime and has
been alive for several hours. Its lock-file identity matches the process ID
reported by `lsof`.

MemPalace 3.6.0 keeps the context manager returned by
`mine_palace_lock(...)` in a module-level variable and registers release with
`atexit`. Once a mutating tool acquires it, the lease is process-lifetime.

Relevant mutations include:

- drawer writes;
- diary writes;
- checkpoints;
- KG mutations;
- MCP mining and sync.

The recent project-memory checkpoints therefore caused or preserved the
writable lease.

### `mempalace_status` is not the cause in 3.6.0

An older MemPalace bug made the read-only status call acquire the writer lease.
That was reported in upstream issue #2013.

The installed 3.6.0 `tool_status()` no longer calls
`_acquire_mcp_writer_lock()`. It uses read-only SQLite paths where possible.
The lease is now acquired lazily on the first mutating MCP tool.

### The GUI read server is not the holder

The current MemPalace GUI starts:

```bash
mempalace serve --read-only --host 127.0.0.1 --port 8766
```

That process is not holding the writer lease.

### The daemon is not the holder

A MemPalace daemon process is running, but it has no active jobs and does not
own the current lease.

Submitting a mine to that separate daemon does not solve the 3.6.0 topology:
the daemon still needs the lease currently held by the writable Copilot MCP
process.

## Why the Lock Exists

MemPalace uses two different lock levels:

1. per-source locks prevent two miners from interleaving delete/reinsert for
   the same file;
2. a per-palace writer lock prevents independent Chroma clients from writing
   the same palace concurrently.

The active lock is the second kind.

On Linux it is an advisory `fcntl.flock`. The pathname can remain after a lock
is released; file existence is not proof that a lock is active. The kernel
lock and its open file descriptor are the authority.

## Do Not Delete the Lock File

Do not remove `mine_palace_*.lock` while the recorded holder is alive.

On POSIX, locks attach to the opened inode. Removing the pathname while one
process still owns the old inode can let a second process create and lock a new
inode at the same path. Both processes can then believe they are exclusive and
write concurrently.

Also avoid:

```text
MEMPALACE_MCP_ALLOW_PEER_WRITER=1
```

in the current multi-process topology. It disables the peer-writer protection
that exists to prevent Chroma/FTS/HNSW divergence.

## Safe Immediate Options on 3.6.0

### Option 1: Mine through the current MCP process

The current writer can run `mempalace_mine` through the MCP tool. The lock is
process-reentrant, so the mine executes inside the process already owning the
lease.

This is safe but does not provide the desired independent manual CLI workflow.

### Option 2: End writable MCP sessions before manual mining

Close or restart every writable MemPalace MCP session, verify that no process
holds the palace lock, and then run the CLI mine.

This is safe but operationally inconvenient.

### Option 3: Reduce the MCP idle lifetime

`MEMPALACE_MCP_IDLE_HOURS` can shorten how long an unused stdio process stays
alive. This only creates an opportunity for the lease to release after the
process becomes idle; it does not allow simultaneous session writes and manual
mines.

It is a mitigation, not an architectural fix.

## Upstream Evidence

The behavior is not unique to this installation.

- [Issue #1888](https://github.com/MemPalace/mempalace/issues/1888) documents
  long-lived MCP writer leases blocking hook-driven and manual mines.
- A production report on 3.6.0 observed 175 refused hook mines, including 66
  held by long-lived MCP processes.
- [Issue #2013](https://github.com/MemPalace/mempalace/issues/2013) documents
  the older status-acquires-lock bug; a contributor reported it fixed by PR
  #1934, and the installed 3.6.0 source independently confirms the
  status-specific call was removed.

Issue #1888 remained open as of 2026-08-25 because lifetime leases still affect
topologies where writers do not route through one process.

## MemPalace 3.8.0 Hub Architecture

The current upstream release is 3.8.0. It contains the architecture needed for
normal manual mines and multi-session agents to share one writer safely.

### How it works

1. Start one writable HTTP MemPalace server for the palace.
2. That process registers itself locally as the palace hub.
3. Per-session stdio `mempalace-mcp` processes discover the hub and become thin
   JSON-RPC proxies.
4. A normal `mempalace mine` discovers the same hub and forwards its
   `mempalace_mine` request over HTTP.
5. All storage mutations occur inside the process that owns the lease.

This is the correct single-writer topology:

```text
Copilot session MCP proxy ─┐
Other agent MCP proxy ─────┼──> writable HTTP hub ──> palace
normal CLI mine ───────────┘
```

The v3.8.0 release also reduces each hub-proxied stdio process to roughly
17–22 MB instead of loading the full Chroma stack in every session.

### Important caveats

Upgrading the package alone is not enough.

If no writable hub is running, a plain stdio process falls back to serving the
palace locally and can still become a lifetime lease holder.

Normal project/conversation/document mines are forwardable. Mines using flags
not represented by the MCP tool retain the direct path and can still be
refused, including:

- explicit backend overrides;
- `--no-gitignore` or `--include-ignored`;
- chunk-cap overrides;
- origin re-detection;
- KG extraction;
- source-adapter paths.

The forwarding code deliberately refuses to use a hub registered as
`read_only`.

## Impact on the Existing MemPalace GUI

The current GUI starts a separate **read-only** HTTP server and routes its
writes/operations through the daemon.

That was a reasonable defensive design for 3.6.0, but it does not solve the
first-writer lifetime lease:

```text
Copilot writable stdio MCP  -> owns lease
GUI read-only HTTP          -> reads work
GUI daemon                  -> write/mine jobs can be refused
manual CLI mine             -> refused
```

For the 3.8.0 hub topology, the GUI should instead:

1. reuse the one writable HTTP hub for reads;
2. send GUI mutations and normal mine requests to that hub;
3. avoid spawning a competing read-only server that registers for the same
   palace;
4. use the daemon only for operations that are intentionally and safely
   coordinated with the hub.

## Recommended Fix for This Setup

Do not disable locking.

Adopt this in a controlled change:

1. back up the palace and verify SQLite/vector integrity;
2. stop current MemPalace MCP, GUI server, and daemon processes cleanly;
3. upgrade MemPalace from 3.6.0 to a reviewed 3.8.x version;
4. start exactly one writable loopback HTTP hub;
5. let Copilot's stdio MCP entry point proxy to that hub;
6. update the MemPalace GUI to reuse the hub for reads and writes;
7. verify that a normal manual mine reports that it is forwarding to the hub;
8. test simultaneous Copilot read/write, GUI read/write, and manual mining on a
   disposable test palace before using the primary palace.

The Workflow Configurator should eventually expose:

- MemPalace version;
- topology: direct stdio versus shared hub;
- active lock holder;
- hub health and read-only status;
- whether a requested mine is forwardable;
- safe launch/restart controls.

It should recommend the shared hub only for multi-session/GUI/manual-mine
setups and retain direct stdio for genuinely simple single-session use.
