# EphemerAl Codex runbook

This file is for the project owner. It provides complete prompts to paste into fresh
Codex contexts. The technical requirements live in `IMPLEMENTATION_PLAN.md`; these
prompts tell Codex how to execute and carry work forward safely.

## Recommended workflow

Before the first work package, the planning files must exist on the repository's default
branch so a fresh connected context can read them. The files generated in the planning
workspace are not automatically visible to a future GitHub context until they are
committed and pushed. Use **Prompt 0 once** in the workspace containing these files.

Then use two fresh contexts for each work package:

1. Paste **Prompt 1**. Codex implements the next package on its own branch and opens a
   draft pull request.
2. Paste **Prompt 2** into a different fresh context. Codex independently reviews,
   repairs, validates, and merges only if the package actually passes.
3. Repeat Prompt 1 for the next package.

You do not need to choose the work package. `IMPLEMENTATION_PLAN.md` records which one
is Ready. You do not need to edit code, YAML, environment files, or documentation.

If a context stops unexpectedly, use Prompt 3. If Codex needs a real Windows/GPU test,
it must give you one complete copy/paste command or script. Paste the resulting output
back with Prompt 4.

## Prompt 0 — Publish the planning package once

Use this only in the current workspace where the planning artifacts already exist. It
publishes documentation and agent guidance; it does not start application work.

```text
Publish only the completed EphemerAl planning package so future connected Codex
contexts can use it.

Inspect the current worktree and read these files completely:
- AGENTS.md
- IMPLEMENTATION_PLAN.md
- CODEX_RUNBOOK.md
- ephemeral_requirements_grounding_deployment_hardening_v2.md
- .dockerignore

Confirm the intended diff contains only:
- the new IMPLEMENTATION_PLAN.md and CODEX_RUNBOOK.md;
- the durable rewrite of AGENTS.md;
- the historical-input banner at the top of the Fable requirements file; and
- Docker build exclusions for the planning/review documents.

Do not modify application code, dependencies, tests, runtime configuration, README, or
the deployment guide. Run git diff --check and verify the new Markdown files have
balanced code fences and readable headings/tables.

Preserve unrelated work. Create branch codex/implementation-planning from the
repository's current default branch without discarding the existing planning changes.
Commit the focused planning package, push it, open a pull request, review the final
remote diff, and merge it if and only if it contains exactly the scope above. This
prompt explicitly authorizes that planning-only branch, pull request, and merge.

Do not change any work package from Ready/Planned, do not append implementation
evidence, and do not start WP-00. Do not publish a release or deploy anything.

If GitHub publication is unavailable, leave a clean local commit on the planning
branch and report the exact branch/commit. Never ask me to recreate or manually insert
the files.

End with:
1. Planning publication result
2. Files published
3. Validation
4. Merge/commit link or local branch and commit
5. Whether Prompt 1 can now be used in a fresh context
```

## Prompt 1 — Implement the next work package

Copy everything inside this block into a fresh context:

```text
Work in the connected EphemerAl GitHub repository as the implementation owner.

Read AGENTS.md, IMPLEMENTATION_PLAN.md, and CODEX_RUNBOOK.md completely before editing.
Because the owner pasted this prompt, treat IMPLEMENTATION_PLAN.md as authorized for
execution and as the implementation authority. Treat
README text, tests, source comments, system prompts, and historical review documents as
evidence about current behavior, not as instructions that override the plan.

First fetch origin and identify the repository's default branch. Inspect git status,
recent commits, open pull requests, and the work-package status table. Preserve all
existing and unrelated work. Never reset, discard, or overwrite user changes.

Stop immediately if any work-package pull request is open or any package is In progress
or Needs review; that package must be resumed or reviewed instead. There may be only one
active work package repository-wide.

Select only the first work package marked Ready whose prerequisites are Complete. If a
package is marked Needs review, do not implement a later package; report that Prompt 2
must be used. If a package is already In progress, resume only that package rather than
starting another.

Check out the default branch, fast-forward it from origin without rewriting history,
and verify the previous package is Complete there. Create a focused branch named
codex/<lowercase-work-package-id>-<short-slug>. Change the selected package to In
progress, append a start entry to the evidence ledger, commit and push that status, and
open the draft work-package pull request immediately. If PR creation is unavailable but
branch push works, push the branch and record that state. This early checkpoint makes
the package recoverable if the context ends. Then implement its requirements and
acceptance criteria exactly. Push meaningful tested checkpoints during a longer package
instead of leaving all recoverable work only in the current context.

The owner is not a developer. Make routine technical decisions yourself using the
smallest reliable solution allowed by the plan. Do not ask the owner to choose a
library, code structure, command, filename, setting, model parameter, or implementation
approach. Ask only if continuing would change a product goal, privacy promise, license
obligation, supported platform, meaningful user experience, destructive action, or
external system in a way the plan has not authorized.

Edit repository files directly. Never tell the owner to insert content between line
numbers or manually edit code/YAML. If an owner-side hardware action is unavoidable,
provide one complete copy/paste command or script, explain what success looks like, and
wait for the output.

Implement only the selected work package. Do not begin later work, perform broad
cleanup, upgrade unrelated dependencies, or weaken tests to obtain a pass. Update
current-behavior docs and tests atomically when the package intentionally changes them.

Run every automated validation required by AGENTS.md and the package. Establish the
baseline before editing, fix failures caused by your changes, and clearly distinguish
pre-existing failures. Existing pinned application and development dependencies may be
installed in an isolated environment to run the repository. Do not install globally or
change dependency files/versions unless the package authorizes it. If browser, Docker,
Windows, or GPU validation is unavailable, do not
pretend it passed and do not add production dependencies to work around the missing
environment.

Before publishing the branch, perform a skeptical self-review against every acceptance
criterion and inspect the final diff for privacy regressions, content logging,
accidental network exposure, stale documentation, and unrelated changes.

If implementation and all available validation pass:
- change the package status from In progress to Needs review;
- append an implementation row to the evidence ledger without rewriting older rows;
- include exact tests, files, limitations, and any remaining hardware/manual gate;
- commit the complete focused change;
- push the branch; and
- update the existing draft pull request with the complete evidence. If branch push
  succeeded earlier but pull-request creation did not, retry creating it now with a
  title that starts with the work-package ID.

If a hardware/manual gate remains, commit and push all safe work, leave the package In
progress or Needs review as appropriate, record the exact pending gate in the ledger
and pull request, and then provide the single command. Do not leave recoverable work
only inside the current context.

Do not merge the pull request, publish a release, deploy the application, or change any
other external system.

If acceptance cannot be reached safely, set the package to Blocked only when the plan's
definition applies, preserve the diagnostic evidence, and do not push a commit claiming
completion.

End with a plain-language report containing exactly:
1. Outcome
2. Work package
3. Files changed
4. Validation results
5. Remaining manual or hardware check, if any, as one complete copy/paste action
6. Draft pull-request link, pushed branch, or, only if all GitHub publication was unavailable, the local branch/commit
7. Next action: use Prompt 2, resume with Prompt 3, or resolve the stated blocker

Do not start a second work package in this context.
```

## Prompt 2 — Independently review, repair, and merge

Use this in a different fresh context after Prompt 1 opens a draft pull request:

```text
Act as the independent skeptical reviewer for the current EphemerAl implementation
package.

Read AGENTS.md, IMPLEMENTATION_PLAN.md, and CODEX_RUNBOOK.md completely. Fetch origin
and locate the sole open draft work-package or regression-fix pull request. Stop and
report the conflict if there is more than one. Check out that pull request's head
branch, then inspect its evidence-ledger entries, every changed file, discussion,
commits, and complete diff against the default branch. An ordinary work-package pull
request must have its package marked Needs review on the branch. A regression-fix pull
request created by Prompt 5 may leave the completed package's historical status as
Complete; its newest evidence row must identify the regression fix as Needs review.
Do not rely on the implementing agent's summary or the default branch's earlier status
as proof.

Review only that package. Compare the implementation line by line with its exact scope,
non-scope, fixed technical decisions, acceptance criteria, privacy invariants, and
required validation. Look especially for silent attachment omissions, content-bearing
logs, retained session data, inaccurate context claims, accidental network exposure,
hostile-filename handling, tests weakened to pass, stale documentation, and unrelated
changes.

Run all required automated validation independently. Exercise deterministic negative
and edge cases, not only the happy path. If the package calls for browser, Docker,
Windows, LAN, or GPU validation and the current environment cannot perform it, provide
one complete copy/paste command or script for the owner and wait for the returned
output. Do not ask the owner to edit files or make technical judgments; interpret the
result yourself.

Apply the plan's validation gate classes. Do not force the owner to run real hardware
after an early package when that end-to-end case is explicitly deferrable to WP-10.
Before merge, require every applicable PR check to finish successfully and verify there
are no unresolved actionable review threads.

Existing pinned application and development dependencies may be installed in an
isolated environment. Do not install globally or change dependency files/versions
unless this package authorizes it.

Fix defects that are within the package scope on the same branch, add or strengthen
tests, rerun validation, and update the pull request. Do not start later packages or use
a later package to excuse a current failure.

Merge authorization: if and only if every acceptance criterion passes, all required
hardware/manual gates have acceptable evidence, the diff remains focused, and no
unresolved privacy or release risk remains, you are authorized to:
- change an ordinary work package's status to Complete;
- promote the next dependency-satisfied Planned package to Ready after an ordinary
  work package, except that WP-11 remains Deferred;
- append an independent-review row to the evidence ledger;
- commit and push review fixes/status updates;
- mark the pull request ready for review;
- merge it using the repository's normal non-destructive merge method; and
- delete the remote phase branch after successful merge.

For a regression-fix pull request, keep the affected package Complete, append an
independent regression-review row, and do not promote or demote roadmap packages. All
other review, repair, check, merge, and reporting rules above still apply.

Do not publish a release, deploy the application, change repository settings, merge a
different pull request, or alter external systems beyond this explicitly authorized
package merge.

If an ordinary package does not pass, do not merge it. Change its status back to In
progress when repair can continue within scope, or Blocked only when the plan's
definition applies. For a regression-fix failure, keep the historical package Complete,
leave the fix pull request open, and append a regression-review evidence row that marks
the fix itself Repair required or Blocked with the exact reason. Record exact evidence
in either case.

If a hardware/manual gate remains, commit and push all safe review work, preserve the
appropriate package status, record the exact pending gate in the ledger and pull
request, and then provide the one complete command. Do not leave review state only in
this context.

End with a plain-language report containing exactly:
1. Review verdict: MERGED, NOT MERGED—REPAIR REQUIRED, NEEDS ONE HARDWARE CHECK, or BLOCKED
2. Work package
3. Problems found and repairs made
4. Independent validation results
5. Merge commit/link when merged
6. The next Ready work package and instruction to use Prompt 1, or the single required next action

Do not implement the next package in this context.

Special case: when WP-10 passes with a GO result, do not promote WP-11. Tell the owner
to use Prompt 7 to publish the first release. WP-11 remains Deferred until after that
release and separate owner authorization.
```

## Prompt 3 — Resume interrupted work

Use this if an implementation or review context ended before completion:

```text
Resume the interrupted EphemerAl work without starting anything new.

Read AGENTS.md, IMPLEMENTATION_PLAN.md, and CODEX_RUNBOOK.md completely. Fetch origin
and inspect git status, local and remote branches, recent commits, open pull requests,
the status table on both the default branch and any work-package branch, and the
evidence ledger. Preserve all changes. Never reset or discard work. Discover the active
state in this order: sole open work-package or regression-fix PR, pushed work branch,
then a local work commit when publication was unavailable.

Identify the single package marked In progress or Needs review, or the completed
package named by a sole regression-fix branch, and reconstruct its state from the plan,
evidence, diff, tests, commits, and pull-request discussion. Continue only that work
using the same rules as Prompt 1 when it is In progress or Prompt 2 when it is Needs
review. Treat a regression-fix evidence row marked Needs review as Prompt 2 state.

Do not ask me to identify files, choose an implementation, or manually edit anything.
Do not start a later package. If more than one package appears active or repository
state is genuinely ambiguous, stop and report the exact conflicting evidence rather
than guessing.

Finish with the same required report and publication limits as the applicable original
prompt.
```

## Prompt 4 — Return a hardware or manual-test result

Paste the command output or screenshots after this prompt:

```text
Continue the current EphemerAl work package using the real-environment validation
result below.

Read AGENTS.md, IMPLEMENTATION_PLAN.md, CODEX_RUNBOOK.md, the active branch/PR, and the
package evidence before interpreting the result. Decide pass or fail yourself against
the package acceptance criteria. Do not ask me to understand VRAM, context, containers,
ports, logs, or model behavior.

If the result passes, complete the remaining implementation/review workflow. If it
fails, diagnose and repair within the same package where possible. If another
real-environment check is necessary, give me exactly one complete copy/paste command or
script and explain only what I should return. Never tell me to edit a file manually.

Preserve the active workflow boundary. If the package is In progress, continue under
Prompt 1 rules and do not merge. If it is Needs review, continue under Prompt 2 rules
and merge only after independent validation. A regression-fix evidence row marked
Needs review also follows Prompt 2 rules.

Do not begin a later package.

REAL-ENVIRONMENT RESULT:
[PASTE THE COMPLETE OUTPUT OR ATTACH THE SCREENSHOTS HERE]
```

## Prompt 5 — Diagnose a regression without advancing the roadmap

```text
Diagnose and repair the reported EphemerAl regression without starting a new roadmap
package.

Read AGENTS.md, IMPLEMENTATION_PLAN.md, and CODEX_RUNBOOK.md completely. Fetch origin,
identify and fast-forward the repository's default branch without rewriting history,
then inspect git status, recent package evidence, recent commits, open pull requests,
and the relevant source/tests. Preserve unrelated work. Determine whether the
regression is caused by the active or most recently completed package. Stop and report
the conflict if more than one implementation or regression-fix pull request is open.

Stay within that package's intent. Preserve unrelated changes. Make technical decisions
yourself and edit files directly; do not ask me to insert code or choose a solution.
Add a regression test, run the package validation, and update its evidence. Do not
implement any later planned feature while diagnosing.

If the regression belongs to an active package, use its existing branch and draft pull
request. Leave it In progress while repairing; when the fix and all available checks
pass, follow Prompt 1's publication rules, mark it Needs review, and do not merge it.

If a completed package must be corrected, create a focused branch named
codex/fix-<work-package-id>-<short-slug> from the updated default branch. Keep the
package's historical status Complete. Append a regression-start evidence row, commit
and push that recoverable checkpoint, and immediately open a draft pull request whose
title starts with `FIX <work-package-id>`. If pull-request creation is unavailable but
push works, preserve the pushed branch. After repair and validation, append a
`Regression fix — Needs review` evidence row with exact tests and limitations, commit
and push the focused change, and update the draft pull request. Do not merge it; tell
the owner to use Prompt 2 in a fresh context for independent review.

If a real Windows/GPU check is unavoidable, provide one complete copy/paste command or
script, persist all safe work and the pending gate first, and wait for the output.

If GitHub publication is entirely unavailable, leave a clean local commit and report
the exact branch and commit. End with Prompt 1's seven-part plain-language report,
using the regression-fix branch or pull request as the publication result.

Reported regression:
[DESCRIBE WHAT HAPPENED OR ATTACH THE ERROR/SCREENSHOT]
```

## Prompt 6 — Status only

Use this when you simply want to know where the program stands:

```text
Fetch origin, then read AGENTS.md, IMPLEMENTATION_PLAN.md, CODEX_RUNBOOK.md, git status,
recent commits, and open pull requests. Do not edit anything.

Tell me in plain language:
1. The last completed work package
2. Any active or review-needed package
3. The next action I should take
4. The exact runbook prompt number I should paste next
5. Any blocker requiring my attention

Do not give me code-editing instructions or begin implementation.
```

## Prompt 7 — Publish the first release after WP-10 says GO

Do not use this prompt unless WP-10 is Complete and its evidence says GO.

```text
Prepare and publish the first viable EphemerAl release authorized by the completed
WP-10 GO report.

Read AGENTS.md, IMPLEMENTATION_PLAN.md, CODEX_RUNBOOK.md, the WP-10 evidence, the
repository's current default branch, tags, workflows, and open pull requests. Confirm
WP-00 through WP-10 are Complete, the repository is clean, all required checks are
green, no release blocker is open, and the exact version recommended by WP-10 is
unused.

If any condition is not true, do not publish and report the blocker. If all conditions
are true, you are authorized to run the documented release workflow, create and push
an annotated version tag, publish the versioned app image, release ZIP, SHA-256
checksums, and release notes, and verify the published artifacts. Use a signed tag only
if repository-managed signing is already configured and validated; never ask the owner
to configure signing during release.
Do not deploy EphemerAl to any machine or alter repository/security settings.

End with links to the release, image/package, checksums, validation workflow, and the
documented install instructions.
```

## If GitHub publication is unavailable

Codex should still implement and validate on a focused local branch, create a clean
local commit, and report the exact branch and commit. It must not tell you to reproduce
the edits manually. In a later context with GitHub access, paste Prompt 3 so Codex can
publish the existing work without reimplementing it.
