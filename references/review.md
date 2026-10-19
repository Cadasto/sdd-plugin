# Review — the findings file, severities, evidence and the forge mirror

The rules for every review of a change, by an agent, a panel host or the maintainer.

## The findings file

A branch's findings live in **one file in the clone's shared git directory**,
`<git-common-dir>/sdd/findings/<branch-slug>.md` (`/` in the branch name becomes `--`; `sdd-pr status`
prints the path): every worktree sees it and git never commits it. It is the
only list of findings, with or without a pull request. `sdd-pr` makes every write (§ The tool).

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
`sdd-pr record`: the commit it read, the agent, the reviewers dispatched and how many reported.  A pass on which no reviewer reported adds none, so its range stays open
until one reads it, or the maintainer's own review is recorded: `pull` records it with their threads, `record --agent maintainer` otherwise.

## Severity

- **critical** — wrong code for an input the specification covers; a security or data-loss risk; a binding sentence the change touches is violated, or no test fails when its guard is removed; a drift
  gate error.
- **important** — a behaviour or contract a caller relies on is missing or wrong; a sentence and the code
  disagree; a SHOULD is unmet with no stated reason.
- **suggestion** — any other lead (below): a test that could be stronger, a cheap refactor, parity the gate does not flag, a document's form.

Severity is the harm, wherever the line is; § Scope says where it is fixed. Critical and important findings in the change are resolved before merge (§ Resolution). Suggestions, an implementer's out-of-scope
leads among them, never block and are never worked unless the maintainer names one. Write one down only when it is a lead: still true without this change's diff, and
improving a behaviour, a test, a contract or a document. Taste (naming, a comment's wording, formatting,
what a linter could enforce), or a keyword missing from a sentence the code meets, is no lead; worth
doing, it is done here. Weigh impact, not effort; unsure, write
it down. A gap in a specification or requirement goes to *Known gaps* or `implementation:
deferred` instead. What the close-out writes (`implementation:` values, acceptance ticks, the changelog
line, the PR body) is no finding before the close-out.

**Code first.** A claim of wrong code behaviour (a wrong result, a crash or hang, a leak, a lost or
corrupted write, an exposure, a refusal the wrong way round) is settled by a run, or by reasoning the
line through with a named input, then graded by its harm; disproven, it is dropped. Neither a missing
run nor a missing specification sentence lowers it, and one a caller can trigger (a write outside its
folder, a crash on bad input) is at least important. A document finding is important only when a reader would build or test the wrong thing from it (sentences, or a sentence and the code, that disagree; an open question settled silently) or a binding change skipped its lane or ADR; otherwise, or unsure, suggestion.
Two reviewers' grades for one defect: the higher one with evidence.

## Scope

A pass reads the whole branch, `merge-base(base, HEAD)..HEAD`; `--since-last` reads only the commits since the last `Reviewed` line (`--agent`: one
agent's own, when it has one) and leaves out what a merge of the base brought in. Plans, the vendored gate unless patched here, and the paths `agents.skip` names go to no reviewer. A stacked branch names its parent once
with `--base`. A critical or
important finding about code, or a document, the branch did not change keeps its
severity and carries `outside`: it blocks nothing and is carried after merge unless the maintainer has it fixed here. Read the changed hunks and what surrounds them, not whole files.

## Evidence

No evidence, no critical or important finding. Code: the input and the observed result (a command run, a
failing test, a guard removed with the test still green), or the line and the rule it breaks.
Conformance: the sentence quoted, the code line, what was run. Documents: the two sentences that
disagree, or the sentence and the code, quoted. One finding names one defect;
other instances inside the range go on the same line.

## The forge mirror

With a pull request, `sdd-pr` keeps its inline threads, one review per pass and the suggestion comments
in step with the file; nothing else about findings is posted. It never writes the pull request's body.

- `pull` appends each unresolved thread the file does not know as an open finding with its `forge:` id;
  a thread is `important` unless it opens with `**critical**`, `outside` when its first line ends `· outside`, and one reopened reopens its line; its `By:` line, when it has one, is the `by:`. A thread with none, not a bot's, is a person's: it records the maintainer's review, a `maintainer` line at the pull request's head. A review body's line in the file's grammar that ends `· outside` becomes an `outside` finding.
- `post` publishes each pass at HEAD as one comment: who reviewed, the blocking verdict, how many lines
  that do not block are new in the pass and open on the branch, then the new ones in one fold, defects
  first. A review is posted only for what sits on a line: one inline thread, carrying its `By:` line,
  per open critical and important finding about the change without a `forge:` id, whose ids are written
  back; a line outside the diff is marked `unanchored` and listed in that review with its evidence. A
  clean pass is its comment alone, once; the maintainer's recorded review gets none.
- `resolve` answers each resolved finding's thread (`fixed in <sha>`, `declined: <reason>` or
  `deferred: <where>`) and closes it.
- `post` and `resolve` put the lines that do not block, posted between passes, in a comment of their own
  (comments are closed threads on Azure DevOps, so no merge policy waits on them), and edit a comment
  whose lines changed, keeping a pass's header; one deleted on the forge is posted again.

The backend is GitHub or Azure DevOps, from `forge:` in the descriptor, else the remote URL, else `none`;
with `none` the file is the whole record and every skill still works.

## Resolution

`sdd-pr flip` resolves a line. `--fixed <sha>` once the fix is pushed; `--declined <reason>`, not argued in a thread; `--deferred <where>`, by the maintainer only: the *Known gaps* line in the specification, the `REQ` that took
`implementation: deferred`, `docs/backlog.md` (`--carry`), or `dropped by the maintainer`. A suggestion
is not declined; dropped once posted, it stays as `- [~]`, so its comment shows it.  A finding has no id,
and commit messages never name one.

## The backlog

Leftovers outlive the findings file in one committed file, `docs/backlog.md`, marked `kind: plan` so the
gate and the reviewers skip it. Its lines sit in themes, each what one delivery would take on: `## <what
that delivery does> (<REQ ids>)`, one sentence, then `- [<severity> · ]<path:line> · <sentence> · from:
<#PR or branch>` lines (a carried one keeps its evidence); themes that hold a defect come first, then
code, tests, other, documents. A line the maintainer wants tracked elsewhere becomes `tracked in <link>`.

`harvest` carries the open lines of the non-blocking comments, an `outside` defect with its severity,
whose path still exists, of every pull request merged after the front matter's `harvested_through:`, and
moves that watermark to the last merge read; the first harvest takes `--since`. With `forge: none` it carries nothing, the close-out having carried the lines, and only names the lines to re-check. `flip --carry` adds a deferred finding, and the close-out's
non-blocking lines when the maintainer carries them in the pull request; its comment then shows them
carried, and `harvest` leaves them out. Both add each line once, under `## Unsorted`, defects first.

`/sdd-triage --backlog` then consolidates. It re-checks the lines `harvest` names because their path
changed since the last harvest, deleting one that is fixed or stale. It moves each Unsorted line into its
theme, or starts one, and folds a line about the same defect into the line already there, keeping the
higher severity and both `from:`. It deletes what falls below the lead bar (§ Severity). A line number
is as of its `from:`, and nobody refreshes it. An item is a lead, not a finding: the delivery whose
`Files` touch its path verifies it, and fixes it or finds it stale.

## Passes

One pass before the maintainer's review (its `maintainer` line), and after each such review at most one
`--since-last` pass over the fixes, a document-only fix included, dispatching only the reviewers whose file kinds changed.
After that only a new critical finding reopens review; otherwise the orchestrator stops and shows the open
list. A second opinion the maintainer asks for is outside this budget.

## Keywords added during review

Behaviour of the shell, a library or the operating system stays informative; a binding sentence is added
only when the code itself guarantees the behaviour and a cheap test can pin it.

## The tool

`sdd-pr` is `python3 <plugin root>/tools/sdd-pr.py`, not vendored. `pull`, `post`, `resolve`, and `harvest` on a forge, need `gh` (GitHub) or `az` with the `azure-devops` extension (Azure DevOps), signed in; the rest need only git. `--pr`, by default the branch's open pull request, must
name one whose branch, or head, this checkout holds, and `--branch` the checkout itself;
otherwise the command stops and names the worktree to run from. A checkout under another name that holds
the pull request's head works on that pull request's file. `add --help` prints the line grammar;
`--version` names the plugin root, and a newer `sdd-pr` installed beside this one is named on every run. `Base:` follows a retargeted pull
request. A plugin older than the repository's `check.version` refuses every write, and `status` says so.

- `status [--pr N]` — the file's path, the open counts, and each open line and suggestion
  with a `#key` that no other line's flip moves;
  on a forge, the threads the file does not know and the checks;
  then `Mergeable: yes` or `Mergeable: no — <reasons>` (no pull request, a closed one or an unreachable
  forge is a reason), and `Next: <command>`: `post` while a line is not on the pull request, `/sdd-triage` while one blocks,
  `/sdd-review --since-last` after a code change once the maintainer has reviewed, until the pass budget is spent (§ Passes), and `/sdd-close` on a draft with nothing else open. A merged pull
  request at HEAD prints `Mergeable: merged`, what is left to carry, the lines that wait for
  `/sdd-triage --backlog` while its watermark is older than the merge, and `/sdd-close`.
- `start --agent <name> [--pr N] [--since-last] [--lane full|maintenance] [--base <ref>]` — a review pass's
  preparation in one call: the pull request's threads pulled (its head must be in this checkout), the
  pass noted, the lane (the flag, the PR body's `Lane:` line, else `decide` with the normative-line
  count), and under `.sdd/review/<head>/` each reviewer's hunks, the drift gate's new lines, the settled
  lines and one shared brief, listing the binding sentences the range wrote; then the dispatch plan. It never runs the gate: the brief names
  `.sdd/gate-<head>.log` when it exists.
- `scope [--json] [--since-last [--agent <name>]] [--base <ref>] [--diff <kind|reviewer>] [--start <agent>]` — the range a
  pass reads (§ Scope), its paths by kind and the reviewers' paths; `range: empty` when nothing is in it; `normative lines changed: n`, a hint for the lane;
  `--start <agent>` notes a pass and names the passes running beside it (noted under an hour ago); passes run side by side, and `record` clears its own agent's note. `--base` is written to the file; `--diff` prints the range's hunks for one kind or
  one reviewer, the plugin's own reviewers included.
- `add <critical|important|suggestion> <path[:line]> <sentence> [--evidence …] [--fix …] [--by …] [--outside]`, or
  `add -` with a reviewer's fence on standard input — checks the grammar, refuses a critical or important
  finding without evidence, drops `outside` from a line the branch changed, and folds a line with the same anchor and sentence into the first (the higher severity, `outside` only when both say so), and a suggestion into a blocking line on its anchor, a posted one kept as `- [~]`.
- `flip <#key | path:line> --fixed <sha> | --declined <reason> | --deferred <where> | --carry | --dropped`
  — resolves one line; `--fixed` needs the fix on `origin/<branch>` when that exists;  `--suggestions` in
  place of the line applies to every one left and, with `--carry`, to the open `outside` lines.
- `harvest [--since <date | #PR>] [--dry-run]` — § The backlog.
- `record --agent <name> --reviewers <a, b> --reported <n>/<m>` — the `Reviewed` line at HEAD; refuses
  (exit 2) a pass on which no reviewer reported, which still ends it; clears `scope --start`'s note and removes the scratch worktree.
- `guard <path:line> --expect <text> (--delete | --replace <text>) [--timeout <s>] -- <test command>` — removes one guard in the pass's scratch worktree at HEAD, runs the command there, which must first pass unchanged, restores the line, and prints `pinned` or `untested`; a run past the timeout (600 s) is a failure. It refuses when `PYTHONPATH` or `NODE_PATH` reaches the file in the checkout. The worktree holds only what HEAD tracks, so a test that needs untracked inputs (installed dependencies, generated files) fails unchanged there, and guard refuses. `--cleanup` removes the
  worktree. It never touches the checkout or the findings file.
- `rename --from <branch>` — moves a file to the checked-out branch without its `Reviewed` lines, thread
  and comment ids, which belonged to the old branch.
- `clean [<branch>] [--pr N] [--dry-run]` — after the merge, from any checkout: removes the branch's
  worktree, the branch (only when it holds no commit the merged pull request lacks; with `forge: none`,
  once in the base), its findings file and delivery notes; refuses, changing nothing, while a line would be
  lost or a worktree holds uncommitted work, and refuses the base, the default branch and, unnamed, a
  branch with no findings file or notes. A worktree it runs in is left, with the commands; the pull request
  and the remote branch are never touched.
- `pull`, `post [--dry-run]`, `resolve` — § The forge mirror.

Exit `0` when the command ran, whether or not the branch is mergeable; `2`, with the reason on standard error, when it refused or failed.
