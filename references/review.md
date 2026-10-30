# Review — the findings file, severities, evidence and the forge mirror

The rules for every review of a change, whoever reviews it.

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
`sdd-pr record`: the commit it read, the agent, the reviewers dispatched and how many reported; a pass
on which no reviewer reported adds none. The maintainer's review is a `maintainer` line: `pull` writes it
with their threads, `record --agent maintainer` otherwise.

## Severity

- **critical** — wrong code for an input the specification covers; a security or data-loss risk; a binding sentence the change touches is violated, or no test fails when its guard is removed; a drift
  gate error.
- **important** — a behaviour or contract a caller relies on is missing or wrong; a sentence and the code
  disagree; a SHOULD is unmet with no stated reason.
- **suggestion** — a lead with no behaviour claim: a test that could be stronger, a cheap refactor, parity the gate does not flag.

Severity is the harm, wherever the line is; § Scope says where it is fixed. Critical and important findings in the change are resolved before merge (§ Resolution). Suggestions never block. A suggestion is written only when it names a path, an input and the weaker or
missing result, is still true without this change's diff, and improves a behaviour, a test or a contract: at most five per reviewer per pass, the rest named in the hand-back. Taste (naming, a comment's wording, formatting,
what a linter could enforce), a keyword missing from a sentence the code meets, a document's form, or "add a `MUST`", is no lead; worth
doing, it is done here. **Unsure means run it or drop it, never write it down.** A gap in a specification or requirement goes to *Known gaps* or `implementation:
deferred` instead. What the close-out writes (`implementation:` values, acceptance ticks, the changelog
line, the PR body) is no finding before the close-out.

**Wrong behaviour is never a suggestion.** A claim of wrong code behaviour (a wrong result, a crash or hang, a leak, a lost or
corrupted write, an exposure, a refusal the wrong way round) is settled by a run, or by reasoning the
line through with a named input, then graded by its harm; disproven, it is dropped. Neither a missing
run nor a missing specification sentence lowers it, and one a caller can trigger (a write outside its
folder, a crash on bad input) is at least important. A sentence and the code that disagree is a defect
in whichever side is wrong: the maintainer's instruction decides, else the branch's own sentence is
corrected ([sdd-methodology.md](sdd-methodology.md) §6, §7). A document finding is important only when a reader would build or test the wrong thing from it (two merged documents that disagree; a sentence that contradicts the code on a contract; an open question settled silently) or a binding change skipped its lane or ADR; a slip in a document this branch wrote is a fix, not a finding (§ Document fixes).
Two reviewers' grades for one defect: the higher one with evidence.

## Scope

A pass reads the whole branch, `merge-base(base, HEAD)..HEAD`, unless the maintainer asks for `--since-last`, which reads the commits since the last `Reviewed` line and leaves out what a merge of the base brought in. Plans, the vendored gate unless patched here, and the paths `agents.skip` names go to no reviewer. A stacked branch names its parent once
with `--base`. **A defect in a file the branch changed is in scope, whatever severity it was filed at:**
fixed in the branch or declined with a reason; the pass budget limits reviewing, never fixing. A critical or
important finding about code, or a document, the branch did not change keeps its
severity and carries `outside`: it blocks nothing; with a small fix it is fixed here, otherwise the close-out carries it (§ The backlog). Read the changed hunks and what surrounds them, not whole files.

## Evidence

No evidence, no critical or important finding. Code: the input and the observed result (a command run, a
failing test, a guard removed with the test still green), or the line and the rule it breaks.
Conformance: the sentence quoted, the code line, what was run. Documents: the two sentences that
disagree, or the sentence and the code, quoted. One finding names one defect;
other instances inside the range go on the same line.

## Document fixes

A document the branch wrote or changed is corrected, not filed. The document reviewer returns, apart from
its findings, a fix list: one line per slip in the range's own documents — two of the branch's sentences
that disagree, a sentence that no longer matches the branch's code, form that changes how a sentence
binds or reads — as `<path>:<line> · <what to change>`. The review skill saves it under
`.sdd/review/<head>/doc-fixes.md` and names its path and count in the hand-back; `/sdd-triage` alone
applies it, with the pass's other fixes, a binding sentence in `/sdd-specify`'s form, and commits by
path. No findings-file line, no thread, no re-review: a document fix is neither code nor a new
obligation (§ Passes).

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
lines when the maintainer carries them in the pull request; its comment then shows them
carried, and `harvest` leaves them out. Both add each line once, under `## Unsorted`, defects first.

The backlog is short, or it is noise: the close-out carries the open `outside` defects without asking
and the leads the maintainer names, `harvest` the rest after the merge, and the consolidation below
keeps it short.

`/sdd-triage --backlog` then consolidates. It re-checks the lines `harvest` names because their path
changed since the last harvest, deleting one that is fixed or stale. It moves each Unsorted line into its
theme, or starts one, and folds a line about the same defect into the line already there, keeping the
higher severity and both `from:`. It deletes what falls below the lead bar (§ Severity), and keeps the
file at about 40 lines: past that, the oldest leads go, defects stay, and the commit message lists what
was dropped so a line the maintainer wants back is nameable. A line number
is as of its `from:`, and nobody refreshes it. An item is a lead, not a finding: the delivery whose
`Files` touch its path verifies it, and fixes it or finds it stale.

## Passes

One pass before the maintainer's review (its `maintainer` line), and after each such review at most one
more pass, over the whole branch, once the fixes changed code or wrote a MUST (a MUST, SHALL or REQUIRED line added to a specification, or to the constitution on the informative profile, as a new obligation; a sentence corrected or reworded is none).
After that only a new critical finding reopens review; otherwise the orchestrator stops and shows the open
list. A second opinion the maintainer asks for is outside this budget.

## Keywords added during review

A review adds no keyword; a binding sentence is added only through `/sdd-specify`, on
[sdd-methodology.md](sdd-methodology.md) §4's terms.

## The tool

`sdd-pr` is `python3 <plugin root>/tools/sdd-pr.py`, not vendored. `pull`, `post`, `resolve`, and `harvest` on a forge need its CLI, signed in ([install.md](../docs/install.md#host-repository-requirements)); the rest need only git. `--pr`, by default the branch's open pull request,
must be held here, else the command stops and names its worktree; without `--root` or `--branch`,
`start`, `scope`, `add`, `record` and `post` run there instead. `--branch` must name the checkout. A
checkout under another name holding the pull request's head works on its file. `add --help` prints the line grammar;
`--version` names the plugin root, and a newer `sdd-pr` beside this one is named on every run. `Base:` follows a retargeted pull
request. A plugin older than the repository's `check.version` refuses every write, and `status` says so.

- `status [--pr N]` — the file's path, the open counts, and each open line and suggestion
  with a `#key`;
  on a forge, the threads the file does not know and the checks;
  then `Mergeable: yes` or `Mergeable: no — <reasons>` (no pull request, a closed one or an unreachable
  forge is a reason), and `Next: <command>`: `post` while a line is not on the pull request, `/sdd-triage` while one blocks,
  `/sdd-review` after a code change or a written MUST once the maintainer has reviewed, until the pass budget is spent (§ Passes), and `/sdd-close` on a draft with nothing else open. A merged pull
  request at HEAD prints `Mergeable: merged`, what is left to carry, the lines that wait for
  `/sdd-triage --backlog` while its watermark is older than the merge, and `/sdd-close`.
- `start --agent <name> [--pr N] [--since-last] [--lane full|maintenance] [--base <ref>]` — a review pass's
  preparation in one call: the pull request's threads pulled (its head in the checkout it runs in), the
  pass noted, the lane (the flag, the PR body's `Lane:` line, else `decide` with the normative-line
  count), and under `.sdd/review/<head>/` each reviewer's hunks, the drift gate's new lines, the settled
  lines and one shared brief, listing the MUSTs the range added as new obligations (a reworded sentence,
  same subject and polarity, pairs with the line it replaced); then the dispatch plan, which on the
  formal profile holds the document reviewer only when the range changed a normative line, a requirement
  or an ADR. It never runs the gate: the brief names
  `.sdd/gate-<head>.log` when it exists.
- `scope [--json] [--since-last [--agent <name>]] [--base <ref>] [--diff <kind|reviewer>] [--start <agent>]` — the range a
  pass reads (§ Scope), its paths by kind and the reviewers' paths; `range: empty` when nothing is in it; `normative lines changed: n`, a hint for the lane;
  `--start <agent>` notes a pass and names the passes running beside it (noted under an hour ago); passes run side by side, and `record` clears its own agent's note. `--base` is written to the file; `--diff` prints the range's hunks for one kind or
  one reviewer, the plugin's own reviewers included.
- `add <critical|important|suggestion> <path[:line]> <sentence> [--evidence …] [--fix …] [--by …] [--outside]`, or
  `add -` with a reviewer's fence on standard input — checks the grammar, refuses a critical or important
  finding without evidence, drops `outside` from a line the branch changed, and folds a line with the same anchor and sentence into the first (the higher severity, `outside` only when both say so), and another reviewer's suggestion into a blocking line on its anchor, kept as `- [~]`.
- `flip <#key | path:line> --fixed <sha> | --declined <reason> | --deferred <where> | --carry | --dropped`
  — resolves one line; `--fixed` needs the fix on `origin/<branch>` when that exists;  `--suggestions` in
  place of the line applies to every one left and, with `--carry` or `--deferred`, to the open `outside` lines.
- `harvest [--since <date | #PR>] [--dry-run]` — § The backlog.
- `record --agent <name> --reviewers <a, b> --reported <n>/<m>` — the `Reviewed` line at HEAD; refuses
  (exit 2) a pass on which no reviewer reported, which still ends it; clears `scope --start`'s note and removes the scratch worktree.
- `guard <path:line> --expect <text> (--delete | --replace <text>) [--timeout <s>] -- <test command>` — removes one guard in the pass's scratch worktree at HEAD, runs the command there, which must first pass unchanged, restores the line, and prints `pinned` or `untested`; a run past the timeout (600 s) is a failure. The worktree holds only what HEAD tracks, so a test that needs untracked inputs (installed dependencies, generated files) fails unchanged there, and guard refuses. `--cleanup` removes the
  worktree. It never touches the checkout or the findings file.
- `rename --from <branch>` — moves a file to the checked-out branch without its `Reviewed` lines, thread
  and comment ids, which belonged to the old branch.
- `clean [<branch>] [--pr N] [--dry-run]` — after the merge, from any checkout: removes the branch's
  worktree, the branch, its findings file and delivery notes; refuses, changing nothing, while the branch holds a commit the merged pull request lacks, a line would be
  lost or a worktree holds uncommitted work, and refuses the base, the default branch and, unnamed, a
  branch with no findings file or notes. A worktree it runs in is left, with the commands; the pull request
  and the remote branch are never touched.
- `brief [--task <words>]` — prints `references/templates/brief.md` with the branch, worktree, worker skills
  and code index filled, and the dispatch model on standard error; writes nothing.
- `pull`, `post [--dry-run]`, `resolve` — § The forge mirror.

Exit `0` when the command ran, whether or not the branch is mergeable; `2`, with the reason on standard error, when it refused or failed.
