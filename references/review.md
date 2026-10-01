# Review — the findings file, severities, evidence and the forge mirror

The rules for every review of a change, whoever reviews: the in-repo agents, the repository's own
reviewers, an outside reviewer given the `/sdd-review --panel` prompt, the maintainer. The skills cite
this file.

## The findings file

A branch's findings live in **one file in the clone's shared git directory**,
`<git-common-dir>/sdd/findings/<branch-slug>.md` (`/` in the branch name becomes `--`): every worktree
and every agent on the machine sees it, git never commits it, and removing a worktree keeps it. It is the
only list of findings, with or without a pull request. `sdd-pr status` prints its path and, once the pull
request merges, names it for deletion; `sdd-pr` makes every write (§ The tool). A file 0.8.0 left at
`.sdd/findings/` in a checkout moves there on first use.

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
- internal/auth/refresh.go:120 · rename `tok` to `token` · by: cursor
```

One finding is one line: `- [ ]` open, `- [x]` fixed, `- [-]` declined, `- [~]` deferred, then fields
separated by ` · ` (space, middle dot, space): the severity, `path:line`, one plain sentence, then any of
`evidence:`, `fix:`, `by:`, `forge:` (the pull request's thread id), `fixed <sha>`, `declined: <reason>`,
`deferred: <where>`, and the markers `unanchored` and `mirrored` that `sdd-pr` writes. A suggestion line
has no checkbox; a routed one is `- [~] suggestion · …`. Each pass adds one `Reviewed` line with
`sdd-pr record`: the commit it read, the agent, the reviewers dispatched and how many reported. The last
one is where the next pass starts. A pass on which no reviewer reported adds none, so its range stays open
until one reads it, or the maintainer's own review is recorded with `record --agent maintainer`.

## Severity

- **critical** — wrong code for an input the specification covers; a security or data-loss risk; a
  binding sentence the change touches is violated, or no test fails when its guard is removed; a drift
  gate error.
- **important** — a behaviour or contract a caller relies on is missing or wrong; a sentence and the code
  disagree; a SHOULD is unmet with no stated reason.
- **suggestion** — anything else worth writing down: wording, keyword form, parity the gate does not flag,
  style, a cheap refactor, a test that could be stronger.

Critical and important findings are resolved (fixed, declined with the reason, or deferred by the
maintainer) before merge, and only they are mirrored. Suggestions, an implementer's out-of-scope
findings among them: at most ten per pass, then "and n more"; never posted, never worked unless the
maintainer names one. Before merge each is routed, with the maintainer, to a *Known gaps* line, an
`implementation: deferred` requirement or a tracker issue (`deferred: <where>`), or dropped; "drop the
rest" is one answer. Unsure between important and suggestion: write suggestion.

## Scope

A pass reads the commits since the last `Reviewed` line, or `merge-base(base, HEAD)..HEAD` the first
time; `sdd-pr scope` prints the range, its paths as code, tests, documents, other and the vendored gate
(which no one reviews), and the reviewer each code path goes to. A stacked branch names its parent once
with `--base`; a local base that is only behind its remote counts from the remote; a panel member reads
from its own last pass with `--agent`. A critical or
important finding is about a line in that range, or text an earlier fix on this branch wrote; anything
else is a suggestion at most. Read the changed hunks and what surrounds them, not whole files.

## Evidence

No evidence, no critical or important finding. Code: the input and the observed result (a command run, a
failing test, a guard removed with the test still green), or the line and the rule it breaks.
Conformance: the sentence quoted, the code line, what was run. Documents: the two sentences that
disagree, or the sentence and the code, quoted. Run the code when you can. One finding names one defect;
other instances inside the range go on the same line.

## The forge mirror

With a pull request, `sdd-pr` keeps its inline threads, and one block in its body, in step with the
file; nothing else about findings is posted.

- `pull` appends each unresolved thread the file does not know as an open finding with its `forge:` id;
  a thread with no severity word is `important`, and its `By:` line, when it has one, is the `by:`.
- `post` publishes the open critical and important findings without a `forge:` id as one review, one
  inline thread each carrying its `By:` line, and writes the ids back; a finding the forge already carries adopts that thread's
  id instead. A line outside the diff is marked `unanchored` and listed in the review body.
- `resolve` answers each resolved finding's thread (`fixed in <sha>`, `declined: <reason>` or
  `deferred: <where>`) and closes it.
- The review state: `post`, `resolve` and `status --write-body` rewrite one block in the body, between
  the whole-line markers `<!-- sdd:review-state -->` and `<!-- /sdd:review-state -->`, from the file: the
  verdict at the head, the passes, the counts, each deferral. It carries no finding id and is never
  edited by hand; a body rewritten without it gets it back on the next write. Markers that are not one
  balanced pair, a body the forge's limit cannot hold, and a checkout without the file are reported,
  never written over.

The backend is GitHub or Azure DevOps, from `forge:` in the descriptor, else the remote URL, else `none`;
with `none` the file is the whole record and every skill still works.

## Resolution

`sdd-pr flip` resolves a line. A fix flips it to `- [x]` with `fixed <sha>`, once the fix is pushed; a
decline flips it to `- [-]` with `declined: <reason>`, and is not argued in a thread. Only the maintainer
defers: the line flips to
`- [~]` with `deferred: <where>`, the *Known gaps* line in the specification, the `REQ` that took
`implementation: deferred`, or `dropped by the maintainer`; the review state lists each one. A finding
has no id, and commit messages never name one.

## Passes

One pass before the pull request is marked ready, the maintainer's review, and at most one pass over the
fixes, a document-only fix included, dispatching only the reviewers whose file kinds changed. After that
only a new critical finding reopens review; otherwise the orchestrator stops and shows the open list.

## Keywords added during review

Behaviour of the shell, a library or the operating system stays informative; a binding sentence is added
only when the code itself guarantees the behaviour and a cheap test can pin it.

## The tool

`sdd-pr` is `python3 <plugin root>/tools/sdd-pr.py`, not vendored; its commands take turns on the clone's
findings, through a lock in the git directory. `status`, `scope` and the four
commands that write the file need only git (`scope --pr` also reads the pull request); `pull`, `post`
and `resolve` need `gh` signed in (GitHub) or `az` with the `azure-devops` extension signed in (Azure
DevOps). `--pr` defaults to the branch's open pull request. `--pr` must
name a pull request whose branch, or head, this checkout holds, and `--branch` the checkout itself;
otherwise the command stops and names the worktree to run from. `Base:` follows a retargeted pull
request. A plugin older than the repository's `check.version` refuses every write, and `status` says so.

- `status [--pr N] [--write-body]` — the file's path, the open counts, and each open line and suggestion
  with a `#key` computed from what it says, which no other line's flip moves;
  on a forge, the threads the file does not know, the checks and whether the review state is current;
  then `Mergeable: yes` or `Mergeable: no — <reasons>` (no pull request, a closed one or an unreachable
  forge is a reason), and `Next: <command>`: `post` before triage while a blocking line is not mirrored,
  routing when only suggestions are left. A merged pull request at HEAD prints `Mergeable: merged`, what
  the file still holds, and the file to delete; one merged or closed before the head moved is no pull
  request of this branch. `--write-body` rewrites the review state first.
- `scope [--json] [--all] [--base <ref>] [--agent <name>] [--diff <kind|reviewer>]` — the range the next
  pass reads (`--all`: the whole branch), its paths by kind and the reviewers' paths; `range: empty`
  when nothing is new. `--base` is written to the file; `--diff` prints the range's hunks for one kind or
  one reviewer, so no brief carries a diff built by hand.
- `add <critical|important|suggestion> <path[:line]> <sentence> [--evidence …] [--fix …] [--by …]`, or
  `add -` with a reviewer's fence on standard input — checks the grammar, refuses a critical or important
  finding without evidence, and folds an identical line into the first.
- `flip <#key | path:line> --fixed <sha> | --declined <reason> | --deferred <where> | --dropped` —
  resolves one line; `--fixed` needs the fix on `origin/<branch>` when that exists; `--dropped` removes
  a suggestion, and `--suggestions` in place of the line applies to every unrouted one.
- `record --agent <name> --reviewers <a, b> --reported <n>/<m>` — the `Reviewed` line at HEAD; refuses a
  pass on which no reviewer reported.
- `rename --from <branch>` — moves a file to the checked-out branch without its `Reviewed` lines and
  thread ids, which belonged to the old branch.
- `pull`, `post [--dry-run]`, `resolve` — § The forge mirror. `--version` prints the version.

Exit `0` when the command ran, whether or not the branch is mergeable; `2` when a command needs a forge
and there is none, the CLI failed or is missing, the file is malformed (the line is named), the
checkout is not the one named, or the command line is invalid.
