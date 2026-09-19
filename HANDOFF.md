# Handoff: repo status and shared-tree workflow

Written 2026-09-19 by a Claude Code session (Sonnet 5) working alongside the
GLM 5.3 / zcode session that built Milestone 1. Read this before your next
commit or push.

## Repo location

Same working directory as always: `F:\Users\Chris\Websites\AgentMarketplace`.
It now has a GitHub remote it didn't have before:

```
origin  https://github.com/ccharles00/agentbench.git
```

Public repo, under Chris's personal GitHub account (`ccharles00`), not any
org. `main` is the only branch, currently at commit `e333bbe`, on top of the
Milestone 1 commit (`08a1288`).

## You're sharing one local git index/HEAD with at least one other agent

This directory isn't a worktree — it's the same checkout multiple sessions
commit to. That means:

- Don't `git add -A` / `git add .` — stage explicit filenames only
  (`git add -- path/to/file`), so you never accidentally stage or commit
  something another session touched but hasn't finished.
- Run `git status` before committing, and `git log --oneline -5` before
  pushing, so you can see if HEAD moved since you last looked.
- Before `git push`, do a `git pull --rebase` (or confirm `git status` says
  "up to date") in case another session pushed in the meantime — avoids a
  diverged-history mess.
- No `git reset --hard`, `git clean -f`, or `git checkout .` without checking
  `git status` first — could discard another session's uncommitted work.

## Push credentials

`gh auth status` shows this machine logged in as `ccharles00` with `repo`
scope, credential helper `store` (file-based, user-level) — any process
running as this Windows user should inherit the same stored HTTPS
credentials, so `git push` should just work. Worth a one-time sanity check
rather than assuming.

## What changed since Milestone 1

- **License decided** (spec C4, an owner call — Chris made it explicitly):
  code MIT, public dataset CC BY 4.0. New `DATA_LICENSE` file at repo root;
  `LICENSE` now has the real copyright holder (Oak Mountain Digital LLC)
  instead of a placeholder; `README.md` has a License section;
  `TODO_OWNER.md`'s licensing line is checked off; `DECISIONS.md` has a new
  "Owner decisions" section (#17) with the rationale — read that before
  touching licensing again.
- **The repo is now public and live**, not just local. This raises the
  stakes on the existing `.gitignore` rules (`.env`, `private_seed.txt` /
  `PRIVATE_SEED`, `data/private/`) — they were always required by spec
  C3.3/B2.7, but a slip is now immediately visible on GitHub, not just a
  local mistake. Matters most starting Milestone 2, when vendor API keys
  and the harness show up — double-check `git status` before every commit
  once that work begins.
- Project name is still **undecided** — keep using the `agentbench`
  placeholder in code/config until Chris confirms one (the "leaning
  AssayMark" note in `TODO_OWNER.md` is still open, not settled).
- Domain: **don't buy one yet** — per `TODO_OWNER.md`, Milestone 3 launches
  on a free GitHub Pages/Cloudflare Pages subdomain, and a real domain waits
  for traction signals (C5/C6).
