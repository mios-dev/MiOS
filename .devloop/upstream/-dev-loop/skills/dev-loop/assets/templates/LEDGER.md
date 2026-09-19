# Dev Loop ledger (handoff notes; newest last)
Each session/lane appends one entry before it ends or compacts: status, done, next, blockers, unverified. A fresh session reads the last entry, `TASKS.md`, and `git log -10` before doing anything.
