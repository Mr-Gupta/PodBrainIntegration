---
author: unknown
date: 2026-07-20
scope: repo:pod-brain
trigger: "install.sh --server after markdown-mode (--store) already installed; double injection of learnings on every prompt"
source: gotcha

---

## Claim

`pod-brain/install.sh` only **adds** hook entries to `~/.claude/settings.json` — it never removes existing ones. So running `install.sh --server <url>` on a machine that already has the markdown-mode hooks (from an earlier `install.sh --store <path>`) leaves both live, causing double injection (markdown learnings *and* server learnings on every prompt). After switching modes, manually delete the two old settings.json entries whose commands reference `inject.py` and `extract.py` (a `.bak` backup is written automatically). Keep both only if you deliberately want the git-markdown store running in parallel with the server.

## Dead-ends

- Assuming `install.sh --server` migrates or replaces a prior `--store` install — it does not; the old hooks stay unless removed by hand.

## Provenance

Learned while writing work-machine install steps: the machine already had markdown-mode hooks, and re-running install in server mode would have stacked a second set of inject/extract hooks.
