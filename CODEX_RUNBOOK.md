# EphemerAl Codex runbook

This file is for the project owner. It assumes the owner works in the ChatGPT and Codex
websites rather than from a terminal or local development environment. It provides
complete prompts to paste into new chats. The technical requirements live in
`IMPLEMENTATION_PLAN.md`; these prompts tell the agents how to execute and carry work
forward safely.

## Recommended workflow

The planning package is already published. **Prompt 0 is complete; do not use it
again.** `Dev` is the program's working/integration branch. `main` is reserved for the
eventual public release and must not be selected for normal implementation work.

For each work package, follow these browser steps:

1. Open Codex in your web browser.
2. Choose repository `eowensai/EphemerAl`. When Codex offers a branch or starting-point
   choice, choose `Dev` with a capital D.
3. Start a new chat and paste **Prompt 1**. Codex chooses and implements the next Ready
   work package. Do not start another EphemerAl coding chat while it is working.
4. When the task finishes, read its **Outcome**, **Draft pull-request link or Create
   pull request action**, and **Next action**. If Codex shows a **Create pull request**
   button and the report does not already contain a pull-request link, click it. If the
   website asks where the pull request should go, choose `Dev`, not `main`.
5. Copy the pull-request link from Codex's report or from the GitHub page that opens
   after **Create pull request** finishes. Open a new ChatGPT Work conversation. In the
   empty message box, type `@GitHub` and select **GitHub** from the list, then paste
   **Prompt 2** after that mention with the link in the marked place. ChatGPT Work
   independently reviews, repairs when its GitHub access permits, validates, and merges
   only if the package actually passes.
6. If that review reports **MERGED**, the package is done. If it reports **APPROVED FOR
   MERGE**, paste **Prompt 2M** into a new ChatGPT Work conversation with the GitHub
   plugin; it performs the final verification and merge into `Dev`.
7. Repeat from step 1 only when the prior package is merged and the report says to use
   Prompt 1 again.

Do not substitute GitHub's automatic review or an `@codex review` request for Prompt
2. Those can be useful extra signals, but Prompt 2 performs the program's complete
package-specific acceptance review and controlled merge.

You do not need to choose the work package. `IMPLEMENTATION_PLAN.md` records which one
is Ready. You do not need to edit code, YAML, environment files, documentation, or a
Codex setup script. If Codex needs Python packages or other development tools in its
hosted workspace, it must install the repository's pinned dependencies itself.

If a Codex task stops unexpectedly before creating a pull request, reopen that same
task from Codex's chat/history list and paste Prompt 3 there; a different chat cannot
see its unpublished edits. If Codex needs a real Windows/GPU test, it must give you one
complete block to copy into Windows PowerShell and tell you exactly how to open
PowerShell, what to paste, and what result to return. Paste that result back into the
same conversation with Prompt 4; you do not need to interpret it.

## Prompt 0 — Planning publication (completed; do not use)

The planning package completed in merge commit `68427d3`. Prompt 0's historical text
has been removed so it cannot be mistaken for a current instruction. Start with Prompt
1.

## Prompt 1 — Implement the next work package

Copy everything inside this block into a new Codex web task:

```text
Work in the connected EphemerAl GitHub repository as the implementation owner.

Read AGENTS.md, IMPLEMENTATION_PLAN.md, and CODEX_RUNBOOK.md completely before editing.
Because the owner pasted this prompt, treat IMPLEMENTATION_PLAN.md as authorized for
execution and as the implementation authority. Treat
README text, tests, source comments, system prompts, and historical review documents as
evidence about current behavior, not as instructions that override the plan.

The program integration branch is `Dev`, even though GitHub's repository default is
`main`. Fetch origin, verify that the task started from current `origin/Dev`, and
inspect git status, recent commits, every open pull request in the repository, and the
work-package status table. Explicitly flag any work-package or regression-fix pull
request whose destination/base is not `Dev`. Never check out, modify, or target `main`
in this prompt. Preserve all existing and unrelated work. Never reset, discard, or
overwrite user changes.

Before selecting work, require every required push check on the exact current Dev head
to have completed successfully. If a current-Dev check is pending or failing, stop and
report its exact link/status; do not start a package merely because the table says
Ready.

Stop immediately if any work-package pull request is open or any package is In progress
or Needs review; there may be only one active work package repository-wide. For In
progress work, tell the owner to reopen the original Codex task and paste Prompt 3. For
Needs review work with a pull-request link, tell the owner to use Prompt 2 in a new
ChatGPT Work conversation. If a work-package/regression pull request targets anything
other than `Dev`, identify its link and wrong destination and do not start duplicate
work.

Select only the first work package marked Ready whose prerequisites are Complete. If a
package is not Ready, do not implement or resume it in this new task.

Check out `Dev`, fast-forward it from `origin/Dev` without rewriting history, and verify
the previous package is Complete there. Create a focused branch named
codex/<lowercase-work-package-id>-<short-slug> from that commit. Every pull request
created by this prompt must use `Dev` as its destination/base branch.

Change the selected package to In progress and append a start entry to the evidence
ledger. If this Codex web task can commit, push, and open a draft pull request while it
is still working, publish that checkpoint immediately. If the web task does not expose
mid-task GitHub publication, do not call that a blocker and do not ask the owner to use
a terminal. Continue in the task's managed workspace, implement the package, and
publish the complete focused branch and pull request when the task finishes. The owner
will not start another EphemerAl implementation task in the meantime.

Implement the package requirements and acceptance criteria exactly. When GitHub
publication is available, push meaningful tested checkpoints during a longer package
instead of leaving recoverable work only in transient context.

The owner is not a developer. Make routine technical decisions yourself using the
smallest reliable solution allowed by the plan. Do not ask the owner to choose a
library, code structure, command, filename, setting, model parameter, or implementation
approach. Ask only if continuing would change a product goal, privacy promise, license
obligation, supported platform, meaningful user experience, destructive action, or
external system in a way the plan has not authorized.

Edit repository files directly. Never tell the owner to insert content between line
numbers or manually edit code/YAML. If an owner-side hardware action is unavoidable,
provide one complete copy/paste PowerShell block, first say exactly how to open
PowerShell in Windows, explain what success looks like, and say exactly what output or
screenshots to return. Wait for that result.

Implement only the selected work package. Do not begin later work, perform broad
cleanup, upgrade unrelated dependencies, or weaken tests to obtain a pass. Update
current-behavior docs and tests atomically when the package intentionally changes them.

Run every automated validation required by AGENTS.md and the package. Establish the
baseline before editing, fix failures caused by your changes, and clearly distinguish
pre-existing failures. Existing pinned application and development dependencies may be
installed in an isolated environment to run the repository. Do not install globally or
change dependency files/versions unless the package authorizes it. If browser, Docker,
Windows, or GPU validation is unavailable, do not pretend it passed and do not add
production dependencies to work around the missing environment. Install the repository's
pinned requirements yourself when the hosted workspace needs them; do not ask the owner
to configure a setup script.

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
  title that starts with the work-package ID and `Dev` as the destination/base.

If the Codex web task can produce a diff but cannot open the pull request itself,
finish with the complete reviewable diff and explicitly tell the owner to click the
task's **Create pull request** control. State that the destination/base must be `Dev`.
Do not treat this normal web handoff as total GitHub publication failure.

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
6. Draft pull-request link or the exact **Create pull request** web action still needed
7. Next action: use Prompt 2, resume with Prompt 3, or resolve the stated blocker

Do not start a second work package in this context.
```

## Prompt 2 — Independently review, repair, and merge

After Prompt 1 produces a draft pull request, copy its GitHub link. Open a new ChatGPT
Work conversation. In the empty message box, type `@GitHub` and select **GitHub** from
the list, then paste this entire prompt after that mention and replace the final
placeholder with the link. This is deliberately a different conversation and surface
from the Codex implementation task.

```text
Use the GitHub plugin and act as the independent skeptical reviewer for the linked
EphemerAl implementation pull request.

Work only in repository eowensai/EphemerAl. Read AGENTS.md, IMPLEMENTATION_PLAN.md,
and CODEX_RUNBOOK.md completely from Dev. Inspect every open pull request in the
repository, then resolve the exact linked pull request. It must target Dev and it must
be the only open work-package or regression-fix pull request regardless of destination.
Stop and report the conflict if either condition is false. Never use, modify, or target
main in this prompt.

Inspect the linked pull request's head branch, evidence-ledger entries, every changed
file, discussion, commits, and complete diff against current Dev. An ordinary
work-package pull request must have its package marked Needs review on the branch. A
regression-fix pull request created by Prompt 5 may leave the completed package's
historical status as Complete; its newest evidence row must identify the regression
fix as Needs review. Do not rely on the implementing agent's summary or Dev's earlier
status as proof.

Before independent testing, record the exact current Dev head as reviewed base D and
verify the pull-request branch contains that base. If the branch is behind Dev, update
the same pull-request branch from current Dev and restart inspection from the new diff.
Never open a replacement pull request. If the available tools cannot update the branch,
return NOT MERGED—REPAIR REQUIRED with ready-to-paste instructions for the original
Codex task. From this point through merge, any change to Dev invalidates the review:
update the same pull request and repeat all review and validation against a new D.

Review only that package. Compare the implementation line by line with its exact scope,
non-scope, fixed technical decisions, acceptance criteria, privacy invariants, and
required validation. Look especially for silent attachment omissions, content-bearing
logs, retained session data, inaccurate context claims, accidental network exposure,
hostile-filename handling, tests weakened to pass, stale documentation, and unrelated
changes.

Run all required automated validation independently. Exercise deterministic negative
and edge cases, not only the happy path. If the package calls for browser, Docker,
Windows, LAN, or GPU validation and the current environment cannot perform it, provide
one complete PowerShell block for the owner, first say exactly how to open PowerShell
in Windows, and say exactly what output or screenshots to return. Wait for the result.
Do not ask the owner to edit files or make technical judgments; interpret the result
yourself.

Apply the plan's validation gate classes. Do not force the owner to run real hardware
after an early package when that end-to-end case is explicitly deferrable to WP-10.
Before merge, require every applicable PR check to finish successfully and verify there
are no unresolved actionable review threads.

Existing pinned application and development dependencies may be installed in an
isolated environment. Do not install globally or change dependency files/versions
unless this package authorizes it.

Fix defects that are within the package scope on the same pull-request branch when the
available GitHub/workspace tools permit it, add or strengthen tests, rerun validation,
and update that same pull request. Never open a second or replacement pull request for
review repairs. If the available tools cannot update the existing head branch, return
NOT MERGED—REPAIR REQUIRED with exact, ready-to-paste repair instructions for the
original Codex task. Do not start later packages or use a later package to excuse a
current failure.

Merge authorization: if and only if every acceptance criterion passes, all required
hardware/manual gates have acceptable evidence, the diff remains focused, and no
unresolved privacy or release risk remains, use this exact finalization sequence:
- capture the exact implementation/repaired code head SHA that was independently
  reviewed and tested (reviewed code head A);
- stage an ordinary work package's status as Complete, understanding that this is
  provisional on the pull-request branch until merge into Dev succeeds;
- promote the next dependency-satisfied Planned package to Ready after an ordinary
  work package, except that WP-11 remains Deferred;
- append an independent-review row to the evidence ledger that names the pull-request
  number, reviewed base D, and reviewed code head A;
- for a WP-10 GO result, add `.github/release-candidate.json` containing exactly the
  approved `version`, `wp10_pull_request`, `reviewed_dev_base` D, and
  `reviewed_code_head` A;
- commit and push only the final status/evidence bookkeeping changes, producing final
  pull-request head B;
- inspect the complete A-to-B diff and require it to contain only those authorized
  status/evidence changes plus the WP-10 release-candidate record when applicable;
- mark the pull request ready for review;
- confirm current Dev is still D and the pull-request head is still B, then wait for
  every required GitHub check to pass for that exact D/B pull-request state;
- submit a final GitHub review against exact head B—not only a top-level conversation
  comment—whose body states **APPROVED FOR MERGE** and explicitly names the full D, A,
  and B commit IDs. For WP-10, that review must also explicitly state GO and the WP-10
  pull-request number plus the exact release-version recommendation;
- immediately recheck that current Dev is D, current pull-request head is B, all checks
  for that exact state remain green, and no actionable review thread remains open;
- merge it into `Dev` using the repository's normal non-destructive merge method; and
- record GitHub's merge-result commit as V; verify current Dev is V and its tree/content
  matches exact approved head B; then wait for every required push check on exact V to
  pass and confirm Dev remains V. If any post-merge verification or check fails, report
  the critical discrepancy and do not authorize another package or Prompt 7; and
- delete only the remote work branch after successful merge when the GitHub tool offers
  that safe option. Never delete `Dev` or `main`.

If this ChatGPT Work review cannot perform the merge itself because the completed
review context does not expose the merge action, complete the A-to-B sequence above,
post the approval for exact head B, and mark the pull request ready when possible;
then return **APPROVED FOR MERGE** instead of MERGED. State the pull-request link plus
reviewed base D, reviewed code head A, and approved final head B, and tell the owner to
paste Prompt 2M into a new ChatGPT Work conversation with the GitHub plugin. Do not use
this fallback for missing GitHub permission or inability to create the required GitHub
review against B; report either as a blocker. Do not call the lack of a merge action in
an otherwise completed review a validation failure, and do not ask the owner to use Git
commands.

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
1. Review verdict: MERGED, APPROVED FOR MERGE, NOT MERGED—REPAIR REQUIRED, NEEDS ONE HARDWARE CHECK, or BLOCKED
2. Work package
3. Problems found and repairs made
4. Independent validation results
5. Pull-request link, reviewed base D, reviewed code head A, approved final head B, and verified Dev merge result V/link when merged
6. The next Ready work package and instruction to use Prompt 1, or the single required next action

Do not implement the next package in this context.

Special case: when WP-10 passes with a GO result, do not promote WP-11. Tell the owner
to use Prompt 7 to promote Dev to main. WP-11 remains Deferred until after Prompt 8
publishes the first release and the owner separately authorizes post-release work.

PULL REQUEST TO REVIEW:
[PASTE THE GITHUB PULL-REQUEST LINK HERE]
```

## Prompt 2M — Merge an independently approved pull request in ChatGPT Work

Use this only when Prompt 2 reports **APPROVED FOR MERGE** because the completed
ChatGPT Work review did not expose the final merge action. Open a new ChatGPT Work
conversation. In the empty message box, type `@GitHub` and select **GitHub** from the
list, then paste this entire prompt after that mention and replace the final placeholder
with the same pull-request link used for Prompt 2.

```text
Use the GitHub plugin to finish the independently approved EphemerAl merge.

Work only in repository eowensai/EphemerAl. Read AGENTS.md, IMPLEMENTATION_PLAN.md,
and CODEX_RUNBOOK.md from branch Dev. Inspect every open pull request in the repository,
then resolve only the linked open work-package or regression-fix pull request. It must
target Dev and remain the sole open work-package/regression-fix pull request regardless
of destination. Never modify or merge to main in this prompt.

Before merging, verify all of the following from GitHub rather than relying only on the
prior chat summary:
- the pull request targets Dev;
- it remains the sole open work-package or regression-fix pull request anywhere in the
  repository;
- the evidence ledger identifies the pull-request number and independently reviewed
  base D and code head A;
- the final GitHub review states **APPROVED FOR MERGE**, explicitly names the full D,
  A, and B commit IDs, and was submitted against exact pull-request head B;
- for WP-10, that review also explicitly states GO, the WP-10 pull-request number, and
  the exact release-version recommendation;
- the A-to-B diff contains only the authorized status/evidence bookkeeping changes
  plus the WP-10 release-candidate record when applicable;
- for WP-10, `.github/release-candidate.json` contains the exact approved version,
  pull-request number, reviewed base D, and reviewed code head A;
- current Dev is still D;
- the current pull-request head is still B and has not changed since approval;
- every required GitHub check has completed successfully for that exact D/B pull-
  request state;
- no actionable review thread remains unresolved;
- the diff is limited to the approved work package; and
- the package status/evidence updates required by Prompt 2 are present.

If any check fails or evidence is ambiguous, do not merge. Report the exact problem
and tell me whether to paste Prompt 2 into a new ChatGPT Work conversation or Prompt 3
into the original Codex task.

If every check passes, immediately recheck D, B, checks, and review threads, then merge
the pull request into Dev using the repository's normal non-destructive merge method.
Record GitHub's merge-result commit as V. Verify current Dev is V and its tree/content
matches exact approved head B, then wait for every required push check on exact V to
pass and confirm Dev remains V. If that verification or a check fails, report the
critical discrepancy and do not authorize another package or Prompt 7. Delete the work
branch only if the GitHub tool offers that safe option. Never delete Dev or main. Do
not publish a release, deploy anything, change repository settings, or start the next
work package.

End with:
1. Merge result and link
2. Completed work package
3. Verified Dev merge result V and checks on exact V
4. Next Ready package
5. Exact next runbook prompt to paste

APPROVED PULL REQUEST TO MERGE:
[PASTE THE GITHUB PULL-REQUEST LINK HERE]
```

## Prompt 3 — Resume interrupted work

Use this when a Codex implementation task stopped before it produced a pull request.
Reopen that exact task from Codex's chat/history list and paste this prompt into it. Do
not start a new implementation chat, because unpublished edits belong to the original
hosted task. If the task cannot be reopened but a pull request exists, use Prompt 6 in
ChatGPT instead so it can inspect GitHub and tell you the safe next action.

```text
Resume the interrupted EphemerAl work without starting anything new.

Read AGENTS.md, IMPLEMENTATION_PLAN.md, and CODEX_RUNBOOK.md completely. Fetch origin
and inspect git status, the current managed task/worktree, current `origin/Dev`, recent
commits, every open pull request in the repository, the status table on `Dev` and any
work-package branch, and the evidence ledger. Flag any work-package or regression-fix
pull request that does not target `Dev`. Never use or modify `main`. Preserve all
changes. Never reset or discard work. Discover the active state from this task's
unpublished diff first, then the sole open work-package or regression-fix pull request,
then any pushed work branch.

Reconstruct this task's state from the plan, evidence, unpublished diff, tests, commits,
and any pull-request discussion. Before routing by status, if the sole existing pull
request targets the wrong branch, retarget that same pull request to Dev when it
unambiguously belongs to this task and the tool permits; never open a replacement. If
it cannot be safely retargeted, stop and report the exact wrong destination and link.
Then follow exactly one case:

- If no package work actually started, continue in this same task using Prompt 1 rules
  and select the first eligible Ready package.
- If the package is In progress, resume only that implementation under Prompt 1 rules.
- If the package or regression-fix row is Needs review but no pull request exists,
  finish publishing the existing branch. If this task cannot open it directly, tell the
  owner to click this task's **Create pull request** control and choose `Dev`. Provide
  the exact resulting/pending link or web action, then stop and direct the owner to
  Prompt 2; do not independently review or merge here.
- If the package or regression-fix row is Needs review and its correctly targeted pull
  request exists,
  stop without editing and direct the owner to Prompt 2 in a new ChatGPT Work
  conversation with the exact link. Independent review must not occur here.

Do not ask me to identify files, choose an implementation, or manually edit anything.
Do not start a later package. If more than one package appears active or repository
state is genuinely ambiguous, stop and report the exact conflicting evidence rather
than guessing.

Finish with the same required report and publication limits as the applicable original
prompt.
```

## Prompt 4 — Return a hardware or manual-test result

Return to the exact Codex or ChatGPT Work conversation that gave you the Windows test.
Paste this prompt there, replace the placeholder with the complete PowerShell output,
and attach any screenshots it requested. Do not start a new conversation for the
result.

```text
Continue the current EphemerAl work package using the real-environment validation
result below.

Read AGENTS.md, IMPLEMENTATION_PLAN.md, CODEX_RUNBOOK.md, the active branch/PR, and the
package evidence before interpreting the result. Decide pass or fail yourself against
the package acceptance criteria. Do not ask me to understand VRAM, context, containers,
ports, logs, or model behavior.

If the result passes, complete the remaining implementation/review workflow. If it
fails, diagnose and repair within the same package where possible. If another
real-environment check is necessary, give me exactly one complete PowerShell block,
first say exactly how to open PowerShell in Windows, and explain exactly what output or
screenshots I should return. Never tell me to edit a file manually.

Preserve the active workflow boundary based on the conversation you returned to, not
only on the package status:

- If this is the original Codex implementation task that requested the result,
  continue under Prompt 1 rules and never independently review or merge here, even if
  that task has already changed the package or regression row to Needs review. Publish
  or update the pull request, then direct the owner to Prompt 2 in a new ChatGPT Work
  conversation.
- If this is the separate ChatGPT Work review conversation that requested the result,
  continue under Prompt 2 rules and merge only after the independent review and every
  remaining gate pass.

Do not infer merge authority from In progress or Needs review alone.

Do not begin a later package.

REAL-ENVIRONMENT RESULT:
[PASTE THE COMPLETE OUTPUT OR ATTACH THE SCREENSHOTS HERE]
```

## Prompt 5 — Diagnose a regression without advancing the roadmap

Use this prompt only when Prompt 6 or a prior work report explicitly tells you to use
Prompt 5. Open Codex in your web browser, choose repository `eowensai/EphemerAl`, choose
branch `Dev`, and start a new task. Paste the block below. Replace the final placeholder
with what happened, or paste the prompt and attach the error screenshot in the same
message.

```text
Diagnose and repair the reported EphemerAl regression without starting a new roadmap
package.

Read AGENTS.md, IMPLEMENTATION_PLAN.md, and CODEX_RUNBOOK.md completely. Fetch origin,
fast-forward `Dev` from `origin/Dev` without rewriting history, then inspect git
status, recent package evidence, recent commits, every open pull request in the
repository, and the relevant source/tests. Explicitly flag any work-package or
regression-fix pull request whose destination/base is not `Dev`. Never use, modify, or
target `main`. Preserve unrelated work. Determine whether the regression is caused by
the active or most recently completed package. Stop and report the conflict if more
than one implementation or regression-fix pull request is open, or if an existing one
targets the wrong branch.

Stay within that package's intent. Preserve unrelated changes. Make technical decisions
yourself and edit files directly; do not ask me to insert code or choose a solution.
Add a regression test, run the package validation, and update its evidence. Do not
implement any later planned feature while diagnosing.

If the regression belongs to an active package, use its existing branch and draft pull
request. Leave it In progress while repairing; when the fix and all available checks
pass, follow Prompt 1's publication rules, mark it Needs review, and do not merge it.

If a completed package must be corrected, create a focused branch named
codex/fix-<work-package-id>-<short-slug> from the updated `Dev` branch. Keep the
package's historical status Complete. Append a regression-start evidence row, commit
the status when the Codex web task supports mid-task publication, and implement the
repair. After repair and validation, append a `Regression fix — Needs review` evidence
row with exact tests and limitations, commit the focused change, and open or update one
draft pull request titled `FIX <work-package-id>: <short description>` with `Dev` as
its destination. If Codex exposes pull-request creation only after the task finishes,
provide the reviewable diff and tell the owner to click **Create pull request** and
choose `Dev`. Do not merge it; tell the owner to use Prompt 2 in a new ChatGPT Work
conversation with the GitHub plugin and the pull-request link.

If a real Windows/GPU check is unavoidable, provide one complete PowerShell block,
first say exactly how to open PowerShell in Windows, persist all safe work and the
pending gate first, and say exactly what output or screenshots to return.

If the hosted task has not yet produced a pull request, keep the work in that same task
and give the normal **Create pull request** handoff. Do not tell the owner that a future
chat can recover an unpublished local commit. End with Prompt 1's seven-part
plain-language report, using the regression-fix pull request or web handoff as the
publication result.

Reported regression:
[DESCRIBE WHAT HAPPENED OR ATTACH THE ERROR/SCREENSHOT]
```

## Prompt 6 — Status only

Use this when you simply want to know where the program stands. Open a new ChatGPT Work
conversation. In the empty message box, type `@GitHub` and select **GitHub** from the
list, then paste this prompt after that mention. ChatGPT Work reads GitHub; you do not
need to open Codex or find a branch or pull request first.

```text
Use the GitHub plugin and inspect repository eowensai/EphemerAl. Treat branch Dev as
the authoritative implementation-program record even though GitHub's default branch is
main. Read AGENTS.md, IMPLEMENTATION_PLAN.md, and CODEX_RUNBOOK.md from Dev, recent
commits on Dev, every required check on the exact current Dev head, and every open pull
request in the repository. Explicitly report any work-package or regression-fix pull
request that does not target Dev. Do not edit, merge, close, or create anything.

Tell me in plain language:
1. The last completed work package
2. Any active or review-needed package
3. The next action I should take
4. The exact runbook prompt number I should paste next
5. Any blocker requiring my attention

Do not give me code-editing instructions or begin implementation.
```

## Prompt 7 — Promote the verified release candidate from Dev to main

Do not use this prompt unless WP-10 is Complete and its evidence says GO. Open a new
ChatGPT Work conversation. In the empty message box, type `@GitHub` and select
**GitHub** from the list, then paste this prompt after that mention. This step only
promotes the verified code to `main`; it does not create a tag or publish a release.

```text
Use the GitHub plugin to promote the verified EphemerAl release candidate from Dev to
main.

Work only in repository eowensai/EphemerAl. Read AGENTS.md, IMPLEMENTATION_PLAN.md,
CODEX_RUNBOOK.md, the complete WP-10 evidence from Dev, the merged WP-10 pull request,
its final GitHub review, and `.github/release-candidate.json`. Confirm WP-00, WP-01,
WP-02, WP-04, WP-05, WP-07, WP-08, WP-09, and WP-10 are Complete on Dev; the ledger
names the WP-10 pull-request number, reviewed base D, and reviewed code head A; the
candidate record names the exact same pull request, D, A, and release version; and the
final GitHub review was submitted against final bookkeeping head B, explicitly states
GO, and names that same version, pull request, and full D, A, and B commit IDs. Confirm
no work-package pull request remains open anywhere in the repository and every required
check for the approved WP-10 state is green.

Fetch and compare current Dev and main without rewriting either branch. Inspect the
merged WP-10 pull request. Record its merge-result commit as verified Dev candidate V.
V must be the current Dev head, the tree/content at V must match approved final WP-10
head B, and Dev must contain no later commit. This intentionally verifies content and
the recorded merge result instead of requiring the pre-merge and post-merge commit IDs
to be identical. Require every applicable push check on exact V to be green. Record the
current main head as promotion base M. If main contains unexpected work that is not
already represented in the verified Dev line, or if the comparison is not a clean
promotion of V over M, stop and report the exact conflict. Never force-push, reset,
discard, or bypass changes.

Locate or create one pull request whose head is Dev and whose base/destination is main.
Its title must identify the WP-10-approved release-candidate promotion. Review the
complete Dev-to-main diff, require all applicable checks to finish successfully, and
confirm there are no unresolved actionable review threads or release blockers.

Immediately before merge, verify current Dev is still V, current main is still M, the
promotion pull request still has exact head V and base state M, and every required
check for that exact V/M pull-request state is green. If every condition passes, merge
that promotion pull request into main using the repository's normal non-destructive
merge method. Record GitHub's promotion merge result as R, then verify current main is
R, current Dev is still V, and main's tree/content at R matches V. Wait for every
required push check on exact R to complete successfully and confirm neither branch
moved while those checks ran. Prompt 8 is not authorized unless these post-merge checks
pass. Do not delete Dev or main. Do not create a tag, publish a release, publish an
image/package, deploy EphemerAl, or change repository/security settings in this prompt.

End with:
1. Promotion result and pull-request/merge link
2. Exact approved final WP-10 pull-request head B
3. Exact Dev candidate V promoted
4. Exact original main base M
5. Exact resulting main commit R
6. Checks verified on the exact V/M promotion state and resulting R
7. Whether Prompt 8 may now be used
```

## Prompt 8 — Publish the first release from the promoted main commit

Do not use this prompt until Prompt 7 has successfully merged the WP-10-approved
release candidate into `main`. Open a new ChatGPT Work conversation. In the empty
message box, type `@GitHub` and select **GitHub** from the list, then paste this prompt
after that mention.

ChatGPT Work first checks the release and gives you the exact version, release commit,
and verified Dev commit to paste into GitHub. When it reports **READY FOR OWNER TO RUN
RELEASE WORKFLOW**, do exactly this:

1. Open the [EphemerAl repository](https://github.com/eowensai/EphemerAl) in your
   browser.
2. Click **Actions** near the top of the repository page.
3. In the left sidebar, click **Publish release**.
4. Click **Run workflow** on the right side of the page.
5. In **Use workflow from**, choose `main`.
6. Paste the three values ChatGPT supplied into **Version**, **Release commit**, and
   **Verified Dev commit**. Do not shorten or retype the commit values.
7. Click the green **Run workflow** button. When the new run appears, click it, copy
   that page's complete browser address, and paste the link back into the same ChatGPT
   Work conversation. If a named button or field is missing, paste a screenshot into
   that same conversation instead of guessing.

```text
Use the GitHub plugin to authorize and verify the first viable EphemerAl release. The
repository's manually dispatched GitHub Actions workflow named `Publish release` is the
only publisher; do not try to create a tag, package, image, or GitHub release directly
with a tool that does not support those actions.

Work only in repository eowensai/EphemerAl. Read AGENTS.md, IMPLEMENTATION_PLAN.md,
CODEX_RUNBOOK.md, the WP-10 GO evidence on Dev, and the completed Dev-to-main promotion
pull request. Obtain immutable release commit R from that pull request's recorded merge
result and verified Dev candidate V from its exact reviewed head. Read
`.github/release-candidate.json` at R and obtain the exact approved Version from it.
Confirm the record matches the WP-10 pull request/review, current main is R, current Dev
is V, neither branch has moved since promotion, main's tree/content at R matches V and
the release candidate approved by WP-10, every required check on R is green, and the
repository has no open release blocker. For an initial attempt, the recorded
Version/tag/public outputs must be unused. For recovery of a prior partial attempt,
allow only existing outputs whose version/R/V provenance exactly matches this candidate;
require the exact prior workflow-run link before treating the request as recovery.

Inspect `.github/workflows/release.yml` from main. It must have visible manual inputs
named Version, Release commit, and Verified Dev commit. The workflow must validate
unchanged main/Dev refs, matching trees, and Version equality with the candidate record
inside the workflow before publication; check out exact R; and publish the annotated
tag, versioned GHCR image, ZIP, SHA-256 checksums, release notes, and GitHub release with
provenance tied to R. Confirm pull-request CI tested the same guard/build/package logic
without publication rights. If the workflow is missing or does not enforce those
guards, do not publish and report the release blocker.

If any condition is false or ambiguous, do not publish and report the blocker. If all
conditions pass, immediately recheck current main R, current Dev V, green checks on R,
and either unused outputs for an initial attempt or exact matching version/R/V
provenance for an authorized recovery. Then report **READY FOR OWNER TO RUN RELEASE
WORKFLOW** and give the owner the exact full values for Version, Release commit R, and
Verified Dev commit V. Repeat the browser clicks stated above in plain language and
stop so the owner can run the workflow. Do not claim publication yet.

When the owner pastes the resulting GitHub Actions run link into this same conversation,
resolve that exact run ID. Inspect every job, step, failure log if applicable, artifact,
and final workflow summary. Confirm it used the exact authorized version/R/V values;
all jobs succeeded; the tag resolves to R; the image reports R and has an immutable
digest; the ZIP and checksum agree; release notes and install links are present; and
the GitHub release points to the same tag. If a retryable infrastructure failure
occurs, continue only when every existing tag/artifact/image/release belongs to this
exact same version/R/V attempt and its provenance matches. A fully matching completed
release is a no-op success; a matching partial attempt may complete only its missing
outputs; any mismatch is a blocker. Never replace different artifacts under the same
version or weaken a release check.

Do not modify Dev, deploy EphemerAl to any machine, delete Dev or main, or alter
repository/security settings.

Only after the exact workflow run succeeds and all outputs verify, report PUBLISHED.
End with exact R and V, the tag and its verified R target, and links to the workflow
run, release, image/package with immutable digest, checksums, and documented install
instructions.
```

## If a web task cannot publish its changes

Do not tell the owner that a different future chat can recover an unpublished local
branch or commit. In Codex web, reopen the same task from the chat/history list and use
Prompt 3. When the task has a complete diff, use its **Create pull request** control
and choose `Dev` as the destination. Once a GitHub pull request exists, it—not a local
workspace—is the durable handoff for a new review conversation.
