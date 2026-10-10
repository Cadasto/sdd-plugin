# Review — the findings file, severities, evidence and the forge mirror

The rules for every review of a change, whoever reviews: the in-repo agents, the repository's own
reviewers, an outside reviewer given the `/sdd-review --panel` prompt, the maintainer.

## The findings file

A branch's findings live in **one file in the clone's shared git directory**,
`<git-common-dir>/sdd/findings/<branch-slug>.md` (`/` in the branch name becomes `--`): every worktree
and every agent on the machine sees it, git never commits it, and removing a worktree keeps it. It is the
only list of findings, with or without a pull request. `sdd-pr status` prints its path and, once the pull
request merges, names it for deletion; `sdd-pr` makes every write (§ The tool).

```markdown
# Findings — feat/auth-refresh
Base: main
Reviewed 9c1e2ab · 2026-09-30 · claude: sdd-spec-conformance-reviewer, go-reviewer (2 of 2)
Reviewed 9c1e2ab · 2026-09-30 · cursor: go-reviewer (1 of 1)

## Open
- [ ] critical · internal/auth/refresh.go:88 · a revoked token rotates instead of failing closed (SPEC-AUTH §3) · evidence: TestRefreshRevoked stays green with the check deleted · fix: fail closed · by: claude
- [ ] important · docs/specifications/auth.md:41 · §3 says "rotates"; the code fails closed · evidence: quoted both · fix: amend §3 · by: maintainer · forge: 5893201111

## Resolved
- [x] important · internal/auth/refresh_test.go:40 · no test for the revoked path · by: cursor · fixed 4f0a1c2
- [-] important · scripts/run.sh:12 · Ctrl-C leaves the sampler running · by: claude · declined: the trap on line 3 covers it; checked with kill -INT
- [~] important · internal/auth/refresh.go:140 · a refused refresh is not logged · by: cursor · deferred: SPEC-AUTH § Known gaps

## Suggestions
- internal/auth/refresh.go:120 · rename `tok` to `token` · by: cursor · comment: 2391840077
```

One finding is one line: `- [ ]` open, `- [x]` fixed, `- [-]` declined, `- [~]` deferred, then fields
separated by ` · ` (space, middle dot, space): the severity, `path:line`, one plain sentence, then any of
`evidence:`, `fix:`, `by:`, `forge:` (the pull request's thread id), `comment:` (the comment carrying a
suggestion), `fixed <sha>`, `declined: <reason>`,
`deferred: <where>`, the marker `outside` (§ Scope), and `unanchored` and `mirrored`, which `sdd-pr` writes. A suggestion line
has no checkbox; a carried or deferred one is `- [~] suggestion · …`. Each pass adds one `Reviewed` line with
`sdd-pr record`: the commit it read, the agent, the reviewers dispatched and how many reported. The last
one is where a `--since-last` pass starts. A pass on which no reviewer reported adds none, so its range stays open
until one reads it, or the maintainer's own review is recorded with `record --agent maintainer`.

## Severity

- **critical** — wrong code for an input the specification covers; a security or data-loss risk; a
  binding sentence the change touches is violated, or no test fails when its guard is removed; a drift
  gate error.
- **important** — a behaviour or contract a caller relies on is missing or wrong; a sentence and the code
  disagree; a SHOULD is unmet with no stated reason.
- **suggestion** — anything else worth writing down: wording, keyword form, parity the gate does not flag,
  style, a cheap refactor, a test that could be stronger.

Severity is the harm, wherever the line is; § Scope says where it is fixed. Critical and important
findings in the change are resolved (fixed, declined with the reason, or deferred by the maintainer)
before merge, and only they get inline threads. Suggestions, an implementer's out-of-scope
leads among them, never block and are never worked unless the maintainer names one (§ The forge
mirror, § The backlog). Write one down only when it is a lead: still true without this change's diff, and
improving a behaviour, a test, a contract or a document. Taste (naming, wording, formatting, what a
linter could enforce) is no lead; worth doing, it is done here. Weigh impact, not effort; unsure, write
it down. A gap in a specification or requirement goes to *Known gaps* or `implementation:
deferred` instead.

**Code first.** A claim of wrong code behaviour (a wrong result, a crash or hang, a leak, a lost or
corrupted write, an exposure, a refusal the wrong way round) is settled by a run, or by reasoning the
line through with a named input, then graded by its harm; disproven, it is dropped. Neither a missing
run nor a missing specification sentence lowers it. A document finding is important only when a reader
would build or test the wrong thing from it: sentences, or a sentence and the code, that disagree; an
open question settled silently. Its form is a suggestion. Unsure about a document or taste: suggestion.
Two reviewers' grades for one defect: the higher one with evidence.

## Scope

A pass reads the whole branch, `merge-base(base, HEAD)..HEAD`, so a second reviewer gives a second
opinion on all of it; `--since-last` reads only the commits since the last `Reviewed` line (`--agent`: one
agent's own, when it has one), as the pass over fixes does, and leaves out what a merge of the base brought in. `sdd-pr scope` prints the range, its paths as code, tests, documents, plans and other and the vendored gate
(reviewed only when patched here), and the reviewer each code path goes to. A stacked branch names its parent once
with `--base`; a local base that is only behind its remote counts from the remote. A critical or
important finding about code the branch did not change (a defect older than the branch) keeps its
severity and carries `outside`: it blocks nothing, goes in the non-blocking comment, and is
carried after merge unless the maintainer has it fixed here. Read the changed hunks and what surrounds them, not whole files.

## Evidence

No evidence, no critical or important finding. Code: the input and the observed result (a command run, a
failing test, a guard removed with the test still green), or the line and the rule it breaks.
Conformance: the sentence quoted, the code line, what was run. Documents: the two sentences that
disagree, or the sentence and the code, quoted. Run the code when you can. One finding names one defect;
other instances inside the range go on the same line.

## The forge mirror

With a pull request, `sdd-pr` keeps its inline threads, one review per pass and the suggestion comments
in step with the file; nothing else about findings is posted. It never writes the pull request's body,
which describes the branch.

- `pull` appends each unresolved thread the file does not know as an open finding with its `forge:` id;
  a thread with no severity word is `important`, and its `By:` line, when it has one, is the `by:`.
- `post` publishes one review per pass at HEAD: a summary (verdict, agents, reviewers, the count of lines that do not block) above one inline thread, carrying its `By:` line, per open critical and important
  finding about the change without a `forge:` id, and writes the ids back; a finding the forge already carries adopts that thread's
  id instead. A line outside the diff is marked `unanchored` and listed in the review body. A clean pass
  posts the summary alone (a closed thread on Azure DevOps), once; the maintainer's recorded review gets
  none.
- `resolve` answers each resolved finding's thread (`fixed in <sha>`, `declined: <reason>` or
  `deferred: <where>`) and closes it.
- `post` and `resolve` put the lines that do not block and are not yet posted, `outside` defects above
  suggestions, in one new comment off the diff (a closed thread
  on Azure DevOps), each line taking its id as `comment:`, and edit a comment whose lines changed; one
  deleted on the forge is posted again.

The backend is GitHub or Azure DevOps, from `forge:` in the descriptor, else the remote URL, else `none`;
with `none` the file is the whole record and every skill still works.

## Resolution

`sdd-pr flip` resolves a line. A fix flips it to `- [x]` with `fixed <sha>`, once the fix is pushed; a
decline flips it to `- [-]` with `declined: <reason>`, and is not argued in a thread. Only the maintainer
defers: the line flips to
`- [~]` with `deferred: <where>`: the *Known gaps* line in the specification, the `REQ` that took
`implementation: deferred`, `docs/backlog.md` (`--carry`), or `dropped by the maintainer`. A suggestion
is not declined; dropped once posted, it stays as `- [~]`, so its comment shows it. An `outside` line not
fixed here stays open. A finding has no id,
and commit messages never name one.

## The backlog

Leftovers outlive the findings file in one committed file, `docs/backlog.md`, marked `kind: plan` so the
gate and the reviewers skip it. Its lines sit in themes, each what one delivery would take on: `## <what
that delivery does> (<REQ ids>)`, one sentence, then `- [<severity> · ]<path:line> · <sentence> · from:
<#PR or branch>` lines (a carried one keeps its evidence); themes that hold a defect come first, then
code, tests, other, documents. A line the maintainer wants tracked elsewhere becomes `tracked in <link>`.

`harvest` carries the open lines of the non-blocking comments, an `outside` defect with its severity,
whose path still exists, of every pull request merged after the front matter's `harvested_through:`, and
moves that watermark to the last merge read; the first harvest takes `--since`. Its lines are short: the
comment `from:` names keeps the evidence. `flip --carry` adds a deferred finding, and, with `forge: none`,
the close-out's non-blocking lines. Both add each line once, under `## Unsorted`, defects first.

`/sdd-triage --backlog` then consolidates. It re-checks the lines `harvest` names because their path
changed since the last harvest, deleting one that is fixed or stale. It moves each Unsorted line into its
theme, or starts one, and folds a line about the same defect into the line already there, keeping the
higher severity and both `from:`. It deletes what falls below the lead bar (§ Severity). A line number
is as of its `from:`, and nobody refreshes it. An item is a lead, not a finding: the delivery whose
`Files` touch its path verifies it, and fixes it or finds it stale; the next harvest deletes the line.

## Passes

One pass before the pull request is marked ready, the maintainer's review, and at most one `--since-last`
pass over the fixes, a document-only fix included, dispatching only the reviewers whose file kinds changed.
After that only a new critical finding reopens review; otherwise the orchestrator stops and shows the open
list. A second opinion the maintainer asks for is outside this budget.

## Keywords added during review

Behaviour of the shell, a library or the operating system stays informative; a binding sentence is added
only when the code itself guarantees the behaviour and a cheap test can pin it.

## The tool

`sdd-pr` is `python3 <plugin root>/tools/sdd-pr.py`, not vendored; its commands take turns on the clone's
findings, through a lock in the git directory. `status`, `scope` and the four
commands that write the file need only git (`scope --pr` also reads the pull request); `pull`, `post`,
`resolve` and `harvest` need `gh` signed in (GitHub) or `az` with the `azure-devops` extension signed in (Azure
DevOps). `--pr`, by default the branch's open pull request, must
name one whose branch, or head, this checkout holds, and `--branch` the checkout itself;
otherwise the command stops and names the worktree to run from. `Base:` follows a retargeted pull
request. A plugin older than the repository's `check.version` refuses every write, and `status` says so.

- `status [--pr N]` — the file's path, the open counts, and each open line and suggestion
  with a `#key` that no other line's flip moves;
  on a forge, the threads the file does not know and the checks;
  then `Mergeable: yes` or `Mergeable: no — <reasons>` (no pull request, a closed one or an unreachable
  forge is a reason), and `Next: <command>`: `post` before triage while a blocking line is not mirrored,
  `/sdd-review --since-last` after a code change until the pass budget is spent (§ Passes),
  `post` while a suggestion is not on the pull request (with no forge: carrying or dropping it). A merged pull request at HEAD prints `Mergeable: merged`, what
  the file still holds, and the file to delete, after `/sdd-triage --backlog` while its watermark is
  older than the merge; one merged or closed before the head moved is no pull request of this branch.
- `scope [--json] [--since-last [--agent <name>]] [--base <ref>] [--diff <kind|reviewer>] [--start <agent>]` — the range a
  pass reads (§ Scope), its paths by kind and the reviewers' paths; `range: empty` when nothing is in it; `normative lines changed: n`, a hint for the lane;
  `--start <agent>` notes a pass, and says `pass: running` instead while another agent's note is under an hour old. `--base` is written to the file; `--diff` prints the range's hunks for one kind or
  one reviewer, the plugin's own reviewers included, so no brief carries a diff built by hand.
- `add <critical|important|suggestion> <path[:line]> <sentence> [--evidence …] [--fix …] [--by …] [--outside]`, or
  `add -` with a reviewer's fence on standard input — checks the grammar, refuses a critical or important
  finding without evidence, and folds an identical line into the first.
- `flip <#key | path:line> --fixed <sha> | --declined <reason> | --deferred <where> | --carry | --dropped`
  — resolves one line; `--fixed` needs the fix on `origin/<branch>` when that exists; `--carry` appends it
  to the backlog (§ The backlog); `--dropped` drops a suggestion (§ Resolution), and `--suggestions` in
  place of the line applies to every one left and, with `--carry`, to the open `outside` lines.
- `harvest [--since <date | #PR>] [--dry-run]` — § The backlog.
- `record --agent <name> --reviewers <a, b> --reported <n>/<m>` — the `Reviewed` line at HEAD; refuses a
  pass on which no reviewer reported; clears `scope --start`'s note and removes the scratch worktree.
- `guard <path:line> --expect <text> (--delete | --replace <text>) -- <test command>` — removes one guard
  in the pass's scratch worktree (one per branch, at HEAD, reused), runs the command there without a
  Python bytecode cache, restores the line, and prints `pinned` or `untested`; `--cleanup` removes the
  worktree. It never touches the checkout or the findings file.
- `rename --from <branch>` — moves a file to the checked-out branch without its `Reviewed` lines, thread
  and comment ids, which belonged to the old branch.
- `pull`, `post [--dry-run]`, `resolve` — § The forge mirror. `--version` prints the version.

Exit `0` when the command ran, whether or not the branch is mergeable; `2` when a command needs a forge
and there is none, the CLI failed or is missing, the file is malformed (the line is named), the
checkout is not the one named, or the command line is invalid.
