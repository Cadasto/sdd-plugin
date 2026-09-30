# Review — the findings file, severities, evidence and the forge mirror

The rules for every review of a change, whoever reviews: the in-repo agents, the repository's own
reviewers, an outside reviewer given the `/sdd-review --panel` prompt, the maintainer. The skills cite
this file and keep only their procedure.

## The findings file

A branch's findings live in **one git-ignored file**, `.sdd/findings/<branch-slug>.md` (the branch name
with `/` replaced by `--`), which any agent on the machine, or a person, reads and edits. It is the store
with or without a pull request, the only list of findings, and is deleted when the branch merges.

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

## Suggestions
- internal/auth/refresh.go:120 · rename `tok` to `token` · by: cursor
```

One finding is one line: `- [ ]` open, `- [x]` fixed, `- [-]` declined, then fields separated by ` · `
(space, middle dot, space): the severity, `path:line`, one plain sentence, then any of `evidence:`,
`fix:`, `by:`, `forge:` (the pull request's thread id), `fixed <sha>`, `declined: <reason>`, and the
markers `unanchored` and `mirrored` that `sdd-pr` writes. A suggestion line has no checkbox. Each pass
adds one `Reviewed` line: the commit it read, the agent, the reviewers dispatched and how many reported.
The last one is where the next pass starts.

## Severity

- **critical** — wrong code for an input the specification covers; a security or data-loss risk; a
  binding sentence the change touches is violated, or no test fails when its guard is removed; a drift
  gate error.
- **important** — a behaviour or contract a caller relies on is missing or wrong; a sentence and the code
  disagree; a SHOULD is unmet with no stated reason.
- **suggestion** — anything else worth writing down: wording, keyword form, parity the gate does not flag,
  style, a cheap refactor, a test that could be stronger.

Critical and important findings are resolved (fixed, or declined with the reason) before merge, and only
they are mirrored. Suggestions: at most ten per pass, then "and n more"; never posted, never worked
unless the maintainer names one, dropped with the file. Unsure between important and suggestion: write
suggestion.

## Scope

A pass reads the commits since the last `Reviewed` line, or `merge-base(base, HEAD)..HEAD` the first
time; `sdd-pr scope` prints the range and its paths as code, tests, documents and other. A critical or
important finding is about a line in that range, or text an earlier fix on this branch wrote; anything
else is a suggestion at most. Read the changed hunks and what surrounds them, not whole files.

## Evidence

No evidence, no critical or important finding. Code: the input and the observed result (a command run, a
failing test, a guard removed with the test still green), or the line and the rule it breaks.
Conformance: the sentence quoted, the code line, what was run. Documents: the two sentences that
disagree, or the sentence and the code, quoted. Run the code when you can. One finding names one defect;
other instances inside the range go on the same line.

## The forge mirror

With a pull request, `sdd-pr` keeps its inline threads and the file in step; nothing else about findings
is posted.

- `pull` appends each unresolved thread the file does not know as an open finding with its `forge:` id;
  a thread with no severity word is `important`.
- `post` publishes the open critical and important findings without a `forge:` id as one review, one
  inline thread each, and writes the ids back; a line outside the diff is marked `unanchored` and listed
  in the review body.
- `resolve` answers each resolved finding's thread (`fixed in <sha>` or `declined: <reason>`) and closes it.

The backend is GitHub or Azure DevOps, from `forge:` in the descriptor, else the remote URL, else `none`;
with `none` the file is the whole record and every skill still works.

## Resolution

A fix flips the line to `- [x]` with `fixed <sha>`; a decline flips it to `- [-]` with
`declined: <reason>`, and is not argued in a thread. Only the maintainer defers; a deferred finding
leaves the file as `implementation: deferred` on its requirement, a *Known gaps* line in the
specification, or nothing. A finding has no id, and commit messages never name one.

## Passes

One pass before the pull request is marked ready, the maintainer's review, and at most one pass over the
fixes, dispatching only the reviewers whose file kinds changed. After that only a new critical finding
reopens review; otherwise the orchestrator stops and shows the open list.

## Keywords added during review

Behaviour of the shell, a library or the operating system stays informative. A binding sentence is added
only when the code itself guarantees the behaviour and a cheap test can pin it. On the informative
profile only the constitution binds (methodology §1a).

## The tool

`sdd-pr` is `python3 <plugin root>/tools/sdd-pr.py`, neither installed nor vendored. `status` and `scope`
need only git; `pull`, `post` and `resolve` need `gh` signed in (GitHub) or `az` with the `azure-devops`
extension signed in (Azure DevOps). `--pr` defaults to the branch's open pull request.

- `status [--pr N]` — the open counts and lines; on a forge, the threads the file does not know and the
  checks; then `Mergeable: yes` or `Mergeable: no — <reasons>`, and `Next: <command>`.
- `scope [--json]` — the range the next pass reads and its paths by kind; `range: empty` when nothing is new.
- `pull`, `post [--dry-run]`, `resolve` — § The forge mirror. `--version` prints the version.

Exit `0` when the command ran, whether or not the branch is mergeable; `2` when a command needs a forge
and there is none, the CLI failed or is missing, the file is malformed (the line is named), or the
command line is invalid.
