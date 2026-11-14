# Pilot 1: a dry run, not a result

Stopped on 14 Nov 2026 at the user's request, to start a clean pilot 2 locked once before any build.

Pilot 1 is kept unchanged as a dry run of the bridge between Jig and The Reality Engine. It had three locks
(LOCKS.log), a first take apart that was stopped (void/), and 8 builds voided before they were stored
(C:/dev/jig-trials/builds/void/REASON.md). What it showed:

- The whole path works: Jig pipelines with Claude Opus and GPT-6 Luna (through Codex), FACTS specs, hidden tests
  copied in after the build, the firewall scan, and the engine's stages.
- A ceiling: all four ways of working passed all 36 comparison checks, so these briefs cannot tell them apart.
  Pilot 2 uses harder briefs for the comparison and the take apart.
- Lessons for the run itself: never change files a running engine reads (the parse-failure incident), and fix the
  design before the lock (the take apart was redesigned mid-run).

Its sealed set was never opened.
