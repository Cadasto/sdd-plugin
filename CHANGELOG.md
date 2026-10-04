# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.11.0] - 2026-10-05

Suggestions stay on the pull request, in a comment of their own per review pass, and only leads are
filed; after merge, `/sdd-triage --backlog` carries them to `docs/backlog.md`, so the close-out no longer
does. `sdd-check` changed only its version number. Moving a repository from 0.10.0 is described in
`docs/upgrading.md`.

### Added
- Tools: `sdd-pr post` and `resolve` keep each pass's new suggestions in one pull-request comment of their own (a closed thread on Azure DevOps), each line taking its id as `comment:`, edit it when a line is fixed, carried or dropped, and post again one deleted on the forge.
- Tools: `sdd-pr harvest [--since <date | #PR>] [--dry-run]` carries the open suggestions of every pull request merged after `harvested_through:` in the front matter of `docs/backlog.md`, tagged `from: #<n>`, leaves out those whose path is gone, and moves that watermark.
- Skills: `sdd-triage --backlog` runs the harvest on the default branch and folds near-duplicates in the diff before the commit.
- Docs: `quick-start.md` and `examples.md` describe the harvest; `upgrading.md` covers 0.10.0 to 0.11.0.

### Changed
- Skills: `sdd-review` drops the cap of ten suggestions per pass and files a suggestion only when it is a lead, listing the rest in its hand-back; `sdd-deliver` and `sdd-triage` file an out-of-scope finding only when it is a lead.
- Skills: `sdd-deliver --close-out` brings the suggestion comments up to date instead of asking to carry or drop the suggestions, which it still asks with `forge: none`, and ends with `/sdd-triage --backlog` on a pull request already merged.
- Skills: `spec-driven-development` routes `/sdd-triage --backlog`; the skills drop restatements of `references/review.md` and `references/sdd-check.md`, and their word budgets follow: `sdd-review` 895, `sdd-deliver` 1487, `sdd-scaffold` 1166, `sdd-specify` 884; `sdd-triage` rises to 819 and `references/review.md` to 1989.
- Agents: the three reviewers report leads only among their ten suggestions.
- Tools: `sdd-pr flip --fixed` takes a suggestion; `--dropped` keeps a posted suggestion as `deferred: dropped by the maintainer`; `rename` forgets comment ids too.
- Tools: `sdd-pr status` points `Next` at `post` while a suggestion is not on the pull request, and on a merged one at `/sdd-triage --backlog` until the watermark passes its merge; the pass summary says the suggestions are in their own comment.
- References: `review.md` § Severity defines a lead (still true without the change's diff; improves a behaviour, a test, a contract or a document; taste is none), and `review.md` adds the `comment:` field, the suggestion comments, the harvest and its watermark; methodology §13 names the suggestion comments.
- Templates: `ai-workflow.md` § Review says a suggestion is written down only when it outlives the change and is harvested after merge; the loop and the tooling table name `/sdd-triage --backlog`.
- Hooks: the session-start line names `/sdd-triage --backlog`, as `rules/sdd-context.mdc` does.

## [0.10.0] - 2026-10-02

The pull request's body describes the branch only, leftovers go to a committed backlog, and a delivery runs
its tasks in sequence, with a parallel wave sharing one branch. `sdd-check` changed only its version
number. Moving a repository from 0.9.0 is described in `docs/upgrading.md`.

### Added
- Tools: `sdd-pr flip --carry` appends a line to the committed `docs/backlog.md` (`kind: plan`) under its directory's heading, once, and defers it there.
- References: `review.md` § The backlog: the file, its line format, and the delivery that folds an item in and deletes its line; methodology §2 and `traceability-schema.md` §3 name it the one standing plan.
- References: `scaffold-upgrade.md` offers to fold a hand-kept list of leftovers into `docs/backlog.md`, and proposes `worktree_per_worker: false` once where the old default is left.

### Changed
- Skills: `sdd-deliver` groups small tasks into one, dispatches in sequence by default, and runs a wave in parallel only when its tasks have disjoint `Files`, no unit imports another's, and each is long enough that waiting for the slowest beats running them in turn; it records the split in the delivery notes.
- Skills: a parallel wave shares the orchestrator's worktree and branch, each worker committing only its `Files`; when the wave ends the orchestrator checks its commits and `git status` against them, and the merge and cleanup steps run only for `worktree_per_worker: true`, which commit hooks that stash the tree require.
- Skills: `sdd-deliver --close-out` asks once to carry the suggestions left to the backlog or drop them, and step 3 folds in each backlog item whose path a task's `Files` touch; `sdd-triage` defers a code-level finding with `--carry`.
- Skills: shorter text in all seven, with lower word budgets.
- Agents: `sdd-implementer` commits by path, `git add -- <Files>` then `git commit -- <Files>`, retries on a held index lock a few times, restores by path only, leaves other workers' changes alone, and verifies a backlog item in `Finding` before acting on it.
- Tools: `sdd-pr status` points `Next` at carrying or dropping the suggestions left.
- Templates: `sdd.yaml` defaults `agents.worktree_per_worker` to `false`; `brief.md` names the orchestrator's worktree and the branch unless it is `true`, never the host's per-agent isolation, and carries a backlog item in `Finding`; `task-review.md` limits the diff to the task's `Files`; `ai-workflow.md` says where suggestions go and when a wave runs in parallel; `development-process.md` § The PR body describes the branch, never its review; the `AGENTS.md` template drops the PR body as a lock.

### Removed
- Tools: the review-state block in the pull request's body, `sdd-pr status --write-body` and the `Mergeable` reasons about the block; `post` and `resolve` no longer write the body.
- References: routing each suggestion to a tracker issue, and methodology §13's review-state check.

## [0.9.0] - 2026-10-01

The findings file moves into the clone's git directory and `sdd-pr` makes every write to it. A review
reads the whole branch, so a second agent or model gives a second opinion, and every pass leaves a short
summary on the pull request. A committed plan carries `kind: plan`, and nothing reads or cites it.
Delivery keeps its state in a notes file and names its worker branches. The gate changed: moving a
repository from 0.8.1, re-vendoring first, is described in `docs/upgrading.md`.

### Added
- Tools: `sdd-pr add`, `flip`, `record` and `rename` own every write to the findings file: `add` checks the grammar, refuses a blocking finding without evidence and folds a duplicate into one line; `flip` resolves a line by the `#key` `status` prints or by `path:line`, needs a fix pushed, and routes or drops suggestions; `record` writes the `Reviewed` line at HEAD; `rename` moves a file to the checked-out branch without its passes and thread ids.
- Tools: `sdd-pr scope --since-last` reads only the commits since the last pass, or since one agent's own with `--agent`, which needs it; `--base <parent>` names a stacked branch's base once and keeps it in the file; `--diff <kind|reviewer>` prints the range's hunks, so no brief carries a diff built by hand.
- Tools: `sdd-pr post` writes one review per pass at HEAD with a short summary on top (the verdict, each agent and its reviewers, the suggestion count), the summary alone after a clean pass, a closed thread on Azure DevOps; a hidden marker posts it once, and the maintainer's own recorded review gets none.
- Tools: `sdd-pr status` lists the delivery's worker branches, `<branch>--<task>`, counting one not integrated or still running (no commit yet, or work in its worktree) against `Mergeable` and naming merged ones for removal; it prints the delivery notes' path and names them for deletion once the pull request merged.
- Tools: `sdd-check check --changed-since <ref>` marks with `NEW` each finding the gate did not report at the merge base of `<ref>` and HEAD, and counts them in the summary; `--new-only` prints just those.
- Tools: each posted thread carries its finding's `By:` line, and `pull` reads it back instead of crediting the account that posted it.
- Skills: `sdd-review` and `sdd-deliver` pick each review dispatch's model for the job, a cheaper one the host offers for a small, mechanical check; workers stay on a strong model.
- References: `agents.reviewers` also takes a block map of path patterns to reviewers; `sdd-pr scope` lists each reviewer's paths and the paths no pattern covers.
- Templates: `task-review.md`, the per-task review `/sdd-deliver` hands each reviewer: the brief, the task's diff, the scope test, mutations in a fresh copy only, findings returned inline.
- Hooks: `session-start.sh` reads the plugin version beside itself on every host and says when the vendored gate is older than the plugin, or the plugin older than the repository.
- Docs: `docs/install.md` gives the permission rules that stop the reviewers' prompts on Claude Code, which a plugin cannot set; `docs/examples.md` adds a second-opinion recipe.

### Changed
- Tools: the findings file lives in the clone's shared git directory, `<git-common-dir>/sdd/findings/<branch-slug>.md`, which every worktree sees and no worktree removal deletes; a file left at `.sdd/findings/` in any worktree moves there on first use, `status` prints the path, and commands take turns on it through a lock.
- Tools: `sdd-pr status` says `Mergeable: no` with no pull request, a closed one or an unreachable forge, prints `Mergeable: merged` and the file to delete once the pull request merged, prints each open line and suggestion with its `#key`, points `Next` at `post` while a blocking line is not mirrored, and at routing while suggestions are left.
- Tools: `sdd-pr scope` reads the whole branch by default, however many passes came before; it counts from `origin/<base>` when the local base is only behind it, and lists the vendored gate as `vendored`, apart from the code to review.
- Tools: a document marked `kind: plan` is a temporary working file: `sdd-check` reads it in no family and counts it, refuses one where requirements, specifications or ADRs live, and fails a durable document that links to one; `sdd-pr scope` lists it as `plans`, for no reviewer, even when the range deleted it.
- Tools: `sdd-pr` refuses every write while the plugin is older than the repository's `check.version`.
- Skills: `sdd-review` runs `scope` first and reviews the whole branch, so another agent or model gives a second opinion on all of it, without the open findings in its reviewers' brief; it dispatches the reviewers and paths `scope` names with the hunks `scope --diff` prints, and reads the gate's new findings with `--changed-since`; `--since-last` reviews only the commits since this agent's last pass, and `sdd-triage`'s re-review uses it; the `Reviewed` line names the host and its model.
- Skills: `sdd-review`, `sdd-triage` and `sdd-deliver` write the findings file only through `sdd-pr`; `sdd-deliver --close-out` routes every suggestion left, to a *Known gaps* line, a deferred requirement or a tracker issue, or drops it.
- Skills: `sdd-triage` verifies each finding with its surroundings (the cause, what shares it, other instances, what the fix changes), adds a defect the finding underrates with `sdd-pr add`, and hands a fix's brief what it found.
- Skills: `sdd-deliver` keeps its lane, gate result and tasks in a notes file in the clone's git directory, names worker branches `<branch>--<task>`, integrates them after a trial merge with one regeneration, removes their worktrees and branches, holds the spec still during a wave, quotes a given plan's tasks verbatim, and resumes from the notes before a pull request exists.
- Skills: `sdd-scaffold` ignores `/.sdd/` as a scratch folder and accepts an existing `.sdd/` line; `--upgrade` merges template changes into tuned process documents section by section, finds an existing pull-request template in any case, and offers `kind: plan` to committed plans.
- Skills: shorter bodies that leave each rule to the reference that owns it; `sdd-specify`, `sdd-triage` and `sdd-trace` gain trigger phrases; every skill names the plugin root as the folder that holds its `skills/` folder, which works on Cursor too.
- References: `review.md` names the new location, the commands and the routing of suggestions, and leaves a second opinion the maintainer asks for outside the pass budget; the review state counts suggestions not routed and lists routed ones.
- References: methodology §3 and §9 state the plan model: temporary, committed or not, never cited by a durable document; § Verify before fixing checks what surrounds a finding.
- Templates: `brief.md` gains `Branch`, `Commit` and rules for the worktree, the generator, a committed can-fail control and an inline report, and its `Finding` field carries what triage found around the line; `ai-workflow.md` and `AGENTS.md` name the findings file in the clone's git directory, and the panel prompt pipes its lines to `sdd-pr add -`; the PR checklist in `development-process.md` follows the repository's own changelog policy.
- Hooks: `session-start.sh` reads the findings file from the clone's git directory.
- Docs: `docs/install.md` says how to read the loaded version on Cursor and what to update; `docs/upgrading.md` covers 0.8.1 to 0.9.0.

### Removed
- Tools: `sdd-pr scope --all`, and `/sdd-review --all`: the whole branch is the default.

### Fixed
- Skills: `sdd-scaffold --upgrade` proposes each version's changes, not only 0.8.0's; `sdd-triage` no longer says that `status` leaves out suggestions.

## [0.8.1] - 2026-10-01

A pull request now carries its review verdict in its body, a follow-up that only edits documents is
reviewed, and `sdd-pr` works only on the checkout that holds the pull request. Moving a repository from
0.8.0 is described in `docs/upgrading.md`.

### Added
- Tools: `sdd-pr` keeps a generated review-state block in the pull request's body, rewritten in place by `post`, `resolve` and the new `status --write-body`: the verdict at the head, the passes, the counts and each deferral; `status` counts a missing or stale block against `Mergeable`, and reports unbalanced markers, a body over the forge's limit or a checkout without the findings file instead of writing.
- References: `review.md` gains the deferred state, `- [~] … · deferred: <where>`, which `sdd-pr resolve` answers and closes; the review state lists each deferral.

### Changed
- Skills: `sdd-triage` flips a deferral to `- [~]`, and `sdd-deliver --close-out` writes the review state before it marks the pull request ready.
- References: methodology §13 registers the review state as a `sdd-pr status` check.
- Templates: `development-process.md` § The PR body and `ai-workflow.md` § Review name the review-state block.

### Fixed
- Skills: a follow-up that only edits documents is reviewed: `sdd-review` sends a changed document to `sdd-doc-reviewer` on both lanes, for consistency on the maintenance lane, and a changed MUST or SHOULD sentence to `sdd-spec-conformance-reviewer` with the code it describes; `sdd-triage` re-reviews a document-only fix after the maintainer's review; a range that called for no reviewer gets no `Reviewed` line.
- Agents: `sdd-doc-reviewer` stops with `MISMATCH` when a hunk in its brief is not in the file on disk, instead of reporting clean.
- Tools: `sdd-pr` does not count a `Reviewed` line on which no reviewer reported, `(0 of <m>)`, as a pass, and `status` names a document change since the last pass.
- References: methodology §12 sends a changed document to `sdd-doc-reviewer` on the maintenance lane; `docs/examples.md` says the same.
- Tools: `sdd-pr post` writes each thread's `forge:` id back on GitHub, whose per-review comment listing carries no line; an id still not read back is taken from the pull request's threads.
- Tools: `sdd-pr` stops with exit 2 when `--pr` names a pull request whose branch or head this checkout does not hold, or `--branch` a branch that is not checked out, and names the worktree to run from; the findings file's `Base:` follows a retargeted pull request.
- Docs: `docs/upgrading.md` covers the `Deferred` rows of a pull request that merged before its last fixes were pushed, and gains the steps from 0.8.0 to 0.8.1; `docs/quick-start.md` matches the re-review rule.

## [0.8.0] - 2026-09-30

The review ledger is gone. Findings live in a git-ignored file per branch that any agent on the machine
can read and write; when a pull request exists, one tool mirrors the critical and important ones to its
inline threads on GitHub or Azure DevOps and says what is open and whether the branch is mergeable. A
second profile, informative, keeps the documents as a knowledge base and binds code to one constitution.
Plans and the close-out skill leave the plugin. Moving a repository from 0.7.x is described in
`docs/upgrading.md`.

### Added
- Tools: `tools/sdd-pr.py` — `status`, `scope`, `pull`, `post`, `resolve` for the findings file and its mirror on GitHub or Azure DevOps, with unit tests; not vendored.
- References: `review.md` — the findings file, three severities, scope, evidence, the forge mirror, resolution, the pass budget, the tool contract.
- References: methodology §1a — the formal and informative profiles; `traceability-schema.md` gains `profile: informative`, `paths.constitution` and `forge`.
- Templates: `constitution.md` — the one binding document of the informative profile; the scaffold also writes `.github/PULL_REQUEST_TEMPLATE.md`.
- Skills: `sdd-trace --audit`; `sdd-deliver --close-out`; `sdd-scaffold` asks the profile and ignores `.sdd/`.
- Scripts: `validate.py` enforces word budgets on every skill and the review path, the `sdd-pr` version pin, forge-neutral text and the retired review vocabulary.
- Hooks: `session-start.sh` prints the plugin version, the profile and the open-findings count.

### Changed
- Skills: `sdd-review` reads the range since the last pass, dispatches by profile and by what changed, writes the findings file and mirrors to the pull request; `--all`, `--panel`, `--pr`.
- Skills: `sdd-triage` works the file's open critical and important lines, fixes small edits in-session, flips lines, mirrors, and re-reviews once, only after the maintainer's review.
- Skills: `sdd-deliver` starts on the informative profile without a requirement, reviews before the draft PR opens, briefs workers with quoted clauses, and closes out itself.
- Agents: the three reviewers share one rules section and return findings-file lines with evidence; `sdd-spec-conformance-reviewer` runs the tests and the guard-removal check; `sdd-doc-reviewer` reviews hunks.
- Agents: `sdd-implementer` reads quoted clauses, writes the test first, proves it fails with the guard removed, and starts a bug fix from a failing reproduction.
- Tools: `sdd-check` accepts `profile: formal | informative`, skips the map families on informative, reads `kind: constitution`, skips git-ignored documents, and reports `paths.plans` and `profile: lightweight` as notes.
- Tools: the `links` family fails a link to a git-ignored file, which no clean checkout has.
- Templates: `ai-workflow.md` § Review and the panel prompt use the findings file; `development-process.md` § The PR body is Summary, Spec and traceability, Verification, Notes for review, Checklist; `brief.md` gains `Clauses` and `Reproduce`.
- References: methodology §13 is the merge gate and the pass budget; `artefact-prose.md` keeps the prose rules only; formal accepts a file-form requirements index.
- Hooks: `spec-edit-reminder.sh` speaks only for the constitution on the informative profile; `session-stop.sh` names the findings file.
- Docs: `README.md` and the `docs/` pages are rewritten in plainer language, and `docs/upgrading.md` gains the 0.7.x to 0.8.0 steps.

### Removed
- Skills: `sdd-archive` (now `sdd-deliver --close-out`); the review ledger, finding ids, rounds, the `Deferred` carry-forward, `--from`, `--post`, the session claim line and the close-out checkboxes.
- References and templates: reviewer memory under `docs/.sdd/reviewers/`; `templates/plan.md`; `paths.plans`.
- Agents: `sdd-traceability-auditor` is no longer part of a review pass.
- Hooks: `session-start.sh` no longer lists open pull requests; `sdd-pr status` does.

## [0.7.0] - 2026-09-27

A plan is now a working file: it is never committed, the gate reads nothing under `paths.plans`,
and `/sdd-finalize` is gone because nothing is left to sweep. The close-out sets the requirement to
`shipped` in its own PR. Moving a repository from 0.6.x is described in `docs/upgrading.md`.

### Added
- Tools: the build status `retired`, allowed only on a `deprecated` requirement, with a selftest case.
- Tools: `check.rfc2119.sections` (`section-sign`, `requirement-id`, `either`) chooses which headings open a normative section.
- References: `scaffold-upgrade.md` holds the `/sdd-scaffold --upgrade` procedure, moved out of the skill.
- Docs: `docs/upgrading.md` gains the 0.6.x to 0.7.0 steps.

### Changed
- Tools: a `map-schema` error in `generate` holds back only the requirements index and detail-file status lines.
- Tools: the gate reads nothing under `paths.plans`, and a `paths.plans` that would hide governed documents is a `descriptor` error; a `check.families.plans` line is reported as a note until it is deleted.
- Skills: a plan is a working file: `sdd-deliver` writes it without committing it, the PR body carries the task list, and `sdd-scaffold` lists `paths.plans` in `.gitignore`.
- Skills: `sdd-archive` sets the `REQ` to `shipped`, promotes a `SPEC §` only when the maintainer confirms, and pushes the close-out only after the full gate passes.
- Skills: `sdd-specify` drops the template comment, writes from shipped code only what the code does, and states how to withdraw an unaccepted ADR; `sdd-deliver` drops the plan template's comment.
- Skills: the router triggers on a code-first request; `sdd-review --post` edits the existing ledger comment instead of posting a second one.
- Skills: `sdd-review` takes `--lane` before a PR exists and carries forward the `Deferred` rows of the last merged PR on the same paths; `sdd-review`, `sdd-triage` and `sdd-trace` route a repository with no descriptor to `/sdd-scaffold`.
- Agents: `sdd-implementer` commits the brief's files by explicit path, reports the SHA, and loads `worker_skills` by name; reviewer findings use the ledger's columns; an untested MUST is a blocker.
- Agents: `sdd-doc-reviewer` flags a solution in ADR Context, a plan citation and a leftover template comment; `sdd-traceability-auditor` flags `packages` that are not the implementing code.
- References: `sdd-methodology.md` §6 adds `retired` and says the close-out sets `shipped`; §9 defines the plan as a working file and forbids durable documents from citing one.
- References: `sdd-check.md` owns the gate-invocation rule and the scoped `generate` refusal; `artefact-prose.md` defines ledger rounds and the ledger comment's identity.
- Templates: the build-status vocabulary gains `retired`; `sdd.yaml` gains `check.rfc2119.sections` and loses `plan` and `plans`; the ADR placeholders steer Context and Decision; `brief.md` gains a `Finding` field.
- Hooks: `session-start.sh` drops the active-plans line and `/sdd-finalize`; `spec-edit-reminder.sh` is silent on a plan edit; `session-stop.sh` points to the PR body or the ledger.
- Docs: `README.md` follows the shared Cadasto plugin layout, with badges, requirements, features, and a table of contents; every `docs/` page opens with an orienting paragraph.

### Removed
- Skills: `sdd-finalize`; there is no release sweep, because no plan is committed.
- Tools: the `plans` family, the plan frontmatter contract and the `plan` document kind; `context` prints no `Plans` section.

### Fixed
- Tools: a nested descriptor key's line anchor matches only a direct child, so `check.rfc2119` is never read as `check.families.rfc2119`.
- Docs: `README.md`, `docs/install.md`, and `docs/quick-start.md` no longer say `/sdd-scaffold` stubs the `spec-check` target; it wires the vendored gate.

## [0.6.0] - 2026-09-24

The rules 0.5.0 stated are now enforced: one vendored, versioned, self-testing gate —
`sdd-check` — checks the chain in both directions, lints the prose rules that can be checked
mechanically, and generates every derived index from one source. The descriptor covers the shapes
repositories had to invent. Moving a repository from 0.5.x is described in `docs/upgrading.md`.

### Added
- Tools: `tools/sdd-check.py` — the drift gate: a strict YAML-subset parser, descriptor and map models, and the drift-core families (descriptor, map schema, map to tree, index sync, plans, tree to map, draft reason), with unit tests.
- Tools: path containment is checked at descriptor load for every command, naming the offending key's line; a wrong-shape key or a missing configured code root is a `descriptor` error.
- Tools: a run that verifies nothing never prints OK; a check in which no family ran exits 2, and a document that cannot be decoded is an error.
- References: `sdd-check.md` — the contract of the shared drift gate: families, severities, report format, exit codes, waivers, generated blocks, vendoring and the version pin.
- References: `sdd-methodology.md` §3 the nine document kinds in three zones, §5 excluded areas, §6 per-kind status vocabularies, §10 the ground-truth resolution order and the cross-repo ask lifecycle, §13 the enforcement register.
- References: `traceability-schema.md` — the descriptor's profile, kinds, excluded areas, default mode, upstream relations, `check:` and `hooks:` blocks; two new record fields; generated blocks.
- Tools: `sdd-check` gains the five prose families — document kinds, RFC-2119 grammar and placement, one canonical home, links with fragments, and changelog bullets — with file-level waivers.
- Tools: `sdd-check generate` writes the three index tables and the requirement status lines from one source; `context` prints a requirement's bundle; `selftest` proves each family with a negative fixture.
- Tools: `generate` matches a row by the identifier it cites and, writing nothing, refuses a row with no record, prose inside the markers, or an undecodable file.
- Tools: `generate --verify` prints the refusals a writing run would; a near-miss or orphaned block marker is an error naming its line.
- Tools: `generate` keeps a byte-order mark and each file's dominant line ending, and a failed write names every file already written.
- Tools: the markdown scan closes a fence only on a bare run of its own length; the YAML subset rejects duplicate keys and decodes quoted values alike in block and inline form.
- Templates: `gap-draft.md` — the upstream cross-repo ask with its state lifecycle.
- Hooks: `session-stop.sh` — a one-shot nudge when a session made no commit and leaves uncommitted changes, registered on both hosts; opt out with `hooks.stop_nudge: false`.

### Changed
- References: `artefact-prose.md` — the changelog-bullet and one-home rules are enforced by the gate's `changelog` and `one-home` families.
- References: `cross-repo-gap.md` — the `state:` lifecycle, the disclosure rule, the behaviour-preservation test, and the named `upstream` relations.
- Templates: `sdd.yaml` carries the profile, document kinds, excluded areas, default mode, and the check and hooks blocks.
- Templates: every emitted document declares its kind; the three index tables sit in generated blocks; `ci.md` names the gate and an optional upstream watcher.
- Hooks: `session-start.sh` prints orientation — branch and tree state, active plans, open pull requests when the forge CLI answers without writing into the repository, and the drift-gate verdict or why none came.
- Hooks: the three scripts detect Cursor by a positive payload marker, read the descriptor from the payload's workspace root, and accept quoted, trailing-slash and unwrapped descriptor paths.
- Hooks: `spec-edit-reminder.sh` names the vendored generate command, `/sdd-specify` or `/sdd-archive` for regeneration, and `/sdd-trace` only for the check.
- Scripts: `validate.py` checks links, retired vocabulary and version agreement; `hooks-test.sh` exercises the hooks; CI runs both, the unit tests and selftest on Python 3.9 and 3.x.
- Skills: `sdd-scaffold` vendors and pins the gate, wires the real spec-check target, runs generate, and gains `--upgrade`, which a 0.5.x descriptor with no check block takes without the flag.
- Skills: every gate call site runs `check` from the vendored copy and routes an unvendored repository to `/sdd-scaffold --upgrade`; `generate` and `context` may use the plugin copy.
- Skills: `sdd-trace` runs the gate's context and check commands first; `sdd-specify`, `sdd-archive` and `sdd-triage` write the map and run generate instead of hand-editing an index.
- Skills: `sdd-review` reads a specification's mode when detecting the lane; `sdd-finalize` and `sdd-deliver` name the gate; the router routes drift, lint and regenerate requests.
- Agents: `sdd-traceability-auditor` relays the gate's findings by family, checks only skipped families by hand, and reports plans as the `plans` family does.
- Packaging: `.gitattributes` keeps maintainer settings, scripts and the gate's tests out of exported archives.

### Fixed
- Hooks: the Claude hook commands quote the plugin root and survive an install path containing spaces.
- Docs: the Cursor `afterFileEdit` event is no longer presented as a working edit reminder, and the Cursor hook list names `stop`.

## [0.5.1] - 2026-09-08

### Changed
- References: `sdd-methodology.md` §8 — identifiers are carried by test names and the implementing commit message. A doc comment is not a carrier: it is written for whoever reads the API, in the host language's own convention. §5 drops code comments from the list of places identifiers appear.
- Agents: `sdd-implementer` cites identifiers in test names and its commit message, and is told not to put them in doc comments.
- Templates: the flow diagrams read `CODE + TESTS (tests cite ids)`.

## [0.5.0] - 2026-09-08

The methodology sheds the plan lifecycle and the plugin takes over the delivery pipeline: a plan is a
working file that is flipped to `done` where it lies and swept at the next release, delivery and triage
become skills, and findings live in one ledger per change. Moving a repository from 0.4.x is described in `docs/upgrading.md`.

### Added
- Skills: `sdd-deliver` — the delivery driver: dispatch preconditions, the plan on the branch, `sdd-implementer` fan-out per `agents:`, the per-task gate by lane, round 0 of the ledger, the draft PR, close-out, ready, panel prompts.
- Skills: `sdd-triage` — one review round: every comment channel enumerated, findings merged into the ledger, verified before fixing, the pattern class swept, fixed in the PR, re-review prompts printed.
- Skills: `sdd-finalize` — the release sweep: deletes `done` and `abandoned` plans as the first step of a version bump, after an inbound-link check; the first run also removes a legacy `docs/plans/archive/`.
- Agents: `sdd-implementer` — implements one bounded task from a brief, cites `REQ`/`PROBE` ids, verifies with the named command, and returns `En-route findings`. Denies `Agent` and `Task` through `disallowedTools:` and inherits every other tool the host offers, MCP servers included, so a repository's code index is reachable. On Claude Code it cannot spawn workers; on Cursor, whose subagent frontmatter carries no tool grant, the same rule is a contract the body states.
- References: `sdd-methodology.md` §12 two lanes with the ratchet guard, §13 review discipline (two gates, the ledger as the default, the materiality threshold, collapse-before-add, the reviewer memory path), §14 the keep-list.
- References: `artefact-prose.md` — the findings ledger, the `Deferred` table, completion accounting, and the prose register.
- References: `traceability-schema.md` — the `agents:` and `review_panel` descriptor block and the plan frontmatter contract; `templates/sdd.yaml` carries the matching `agents:` block.
- Templates: `brief.md` — the worker brief `/sdd-deliver` fills per task — and `adr-README.md`, the ADR index the scaffold emits.
- Docs: `docs/quick-start.md` — one capability from scaffold to a ready pull request — and `docs/examples.md`, prompts by use case; `docs/upgrading.md` — the 0.4.x to 0.5.0 migration table.

### Changed
- References: `sdd-methodology.md` §9 is now a working-plan lifecycle — `active | done | postponed | abandoned`, five dispatch preconditions, close-out on four surfaces, archive in place, sweep at the release.
- References: `sdd-methodology.md` §5 states lazy identifier allocation as the default; §10 adds the cross-repo disagreement rule; §11 adds the memoir rule.
- References: `artefact-prose.md` states the changelog-bullet rule and the single-canonical-home rule, both as reviewer rules with no tool behind them yet.
- Skills: every description is trimmed to trigger phrases, purpose, and boundary; bodies drop second person and history-relative phrasing; the plugin-root note is one line; forge commands are qualified per host; `sdd-specify` names the exploration route and ends with a trace check; `sdd-scaffold`'s stub gate fails until a checker is wired.
- Skills: `sdd-deliver` runs on either lane — the maintenance lane owes no `REQ`, plan, or close-out, per methodology §12 — and runs the full build gate before round 0 and before marking ready; `sdd-finalize` ignores inbound links whose source is itself swept; `sdd-trace` accepts an implementation-aligned plan on a shipped `REQ`; `sdd-review` holds no `Write`. The implementer accepts a maintenance brief with no `REQ`; `sdd-review` takes `--lane` when there is no PR and no plan; an empty `agents.reviewers` on the maintenance lane is cleared by the maintainer's own review; the polish classes of §13 go to `Deferred` from both review and triage.
- Manifests: the Cursor manifest carries `repository` and `keywords`; the validator checks license, repository, and keywords for parity.
- Templates: `sdd.yaml` defaults `worker_model` to `inherit`; the manifest description names the delivery pipeline.
- Skills: `sdd-specify` owns spec amendments — any normative change is full lane — and the router sends them there; `sdd-archive` stops when the branch has no plan; `sdd-deliver` keeps the maintenance task list in the PR body.
- Agents: `sdd-implementer` cites only the identifiers its brief names — the `REQ` on the full lane, the preserved `SPEC §` or nothing on the maintenance lane.
- References: `artefact-prose.md` — the maintainer's review is appended to the ledger's accounting line as `maintainer`, where the ready check finds it.
- Skills: `sdd-archive` is reduced to the frontmatter flip, the status updates, and the PR body — no `git mv`, no index.
- Skills: `sdd-review` detects the lane, dispatches per lane, writes one ledger instead of one comment per finding, and prints one canonical prompt block per `review_panel` entry with `--panel`.
- Skills: `sdd-scaffold` no longer creates `docs/plans/archive/` or a plans index, and fills the `agents:` block of the descriptor, suggesting `agents.reviewers` and `agents.worker_skills` from the build manifests in the tree (`go.mod`, `composer.json`, `package.json`) for the maintainer to confirm.
- Skills: `sdd-specify` hands off to `/sdd-deliver` and no longer routes design notes through another plugin.
- Skills: `sdd-trace` reports a plan/`REQ` status mismatch from the plan's frontmatter rather than from a plans index.
- Skills: `spec-driven-development` routes the new surface and states in one paragraph that a general engineering plugin is optional.
- Agents: the three reviewers gain the materiality threshold, the settled-adjudications memory, and the cross-repo rule.
- Agents: the three reviewers route code review to the repository's own declared reviewers and test-passing to the build gate.
- Templates: `plan.md` carries a minimal header; `ai-workflow.md` gains the standing orchestration section with its code-index line, the canonical review-request block, and the ledger rules; `AGENTS.md` mirrors the orchestration rules; `development-process.md` replaces the DoR/DoD blocks with dispatch preconditions, the lanes, and the PR-body close-out with its `Lane:` line.
- Templates: `ci.md` names the build gate directly, and its scheduled drift-bot row fails the run and reports the drift instead of opening a tracking issue.
- Hooks: `session-start.sh` lists the full `/sdd-*` surface and the new plan rule.
- Scripts: `validate.py` requires every agent to declare a grant — `tools:` or `disallowedTools:` — and still rejects `allowed-tools:`.
- Docs: `AGENTS.md`, `README.md`, `docs/authoring.md`, `docs/install.md`, `docs/testing.md`, and `rules/sdd-context.mdc` follow the new surface; the PR template gains the disclosure grep and `.gitignore` excludes the plan workspace.

### Removed
- References: `sdd-with-superpowers.md` and the `docs/superpowers/` path redirect. A general engineering plugin is optional and described in one paragraph in the router.
- References: the `plans:` axis of a traceability record and `paths.plans_archive` from the descriptor and its template.
- Agents: `sdd-doc-reviewer` no longer reviews plan headers; `sdd-traceability-auditor` no longer reports plan drift classes.

## [0.4.1] - 2026-08-25

Corrects three component defects and the claims the docs made about them: a `PostToolUse` hook timeout that was five hours rather than twenty seconds, an always-on router that inherited every tool, and two agents that described themselves as read-only while holding `Bash`.

### Changed
- Docs: `README.md` — the agents table was headed **read-only**, which holds for one of the three. `sdd-doc-reviewer` declares only `Read`/`Grep`/`Glob` and is read-only outright; `sdd-traceability-auditor` and `sdd-spec-conformance-reviewer` add `Bash`, which writes. The heading is now **report-only**, with a line saying which guarantee is enforced and which is a contract the agent keeps. `/sdd-trace` is relabelled the same way — it declares `Bash` too.
- Docs: `docs/authoring.md` — the authoring rule now depends on the grant rather than habit: call an agent read-only only when its `tools:` genuinely are, and describe one holding `Bash` as report-only. `docs/testing.md` follows for `/sdd-trace`.
- Docs: sentence-case H1s in `docs/testing.md`, `docs/versioning.md`, `docs/authoring.md`; "for example" over "e.g."; `docs/testing.md` opens with its subject rather than "There is"; the superpowers seam paragraph no longer opens with "So".
- Docs: `docs/versioning.md`, `AGENTS.md` — the marketplace no longer tracks this repo's default branch. The Cadasto catalog pins each entry to a release tag, so a release is not live until the entry in `Cadasto/plugin-marketplace` bumps `version` and `source.ref`; added as release step 8.

### Fixed
- Hooks: the `PostToolUse` reminder declared `"timeout": 20000`. Claude Code reads a hook timeout in **seconds** (`hook.timeout * 1000` internally), so that was 5 hours 33 minutes, not 20 seconds — a hung script would have stalled the session rather than being cut off. Now `20`.
- Skills: `spec-driven-development` declared no `allowed-tools`, so the always-on router inherited **every** tool including `Write`, `Edit`, and `Bash`. It explains and routes — it reads the references and `docs/.sdd.yaml` and does no artefact work — so it now declares `Read, Grep, Glob`.
- Agents: `sdd-traceability-auditor` and `sdd-spec-conformance-reviewer` described themselves as **read-only** while declaring `Bash`, which writes. Both are **report-only**, and each body now says no-edit is a contract it keeps rather than a sandbox that keeps it. `sdd-doc-reviewer` is unchanged: it declares only `Read`/`Grep`/`Glob`, so read-only is accurate there.

- Docs: `claude plugin add` is not a Claude Code command. `README.md`, `docs/install.md`, `docs/versioning.md` (the dogfood release step), and `AGENTS.md` load a local working copy with `claude --plugin-dir <path>`, which applies to that session only.

## [0.4.0] - 2026-08-05

### Changed
- References: `sdd-methodology.md` defines the **negative space** discipline — §3: acceptance criteria cover what the capability must refuse or fail closed on, with the intended failure behaviour; §9 DoR names it (cited from the `REQ`/`SPEC §`, not restated) and §9 DoD exercises it (refusal paths tested, new runtime failure modes mapped to the error contract — the RFC-2119 `SPEC §` owning failure behaviour); §4: fail-closed clauses carry the same force as positive ones; §11: happy-path-only acceptance is an anti-pattern. Templates `requirement.md`, `plan.md`, and `development-process.md` mirror.
- Skills: `sdd-specify` authors the negative space at the right altitude — §A the `REQ` names and cites it as an observable outcome, §B the spec owns the normative *how* (`MUST NOT`/fail-closed/error contract); `sdd-archive` blocks the archive on unmet plan-DoD boxes (negative space exercised included).
- Skills: `sdd-review` lands best before the PR is opened (findings fold into the slice instead of becoming post-publication review rounds); the generic reviewer runs report-only until the post step, and scoping no longer assumes an open PR.
- Agents: `sdd-doc-reviewer` flags happy-path-only acceptance criteria, a DoR with no named negative space, and a `done` plan with unchecked DoD boxes; `sdd-spec-conformance-reviewer` enumerates negative-space criteria as first-class clauses (an untested refusal path is a finding).
- Agents: system prompts now open in second person ("You are…") per agent-authoring guidance; `docs/authoring.md` records the convention.
- Skills, agents: trimmed the always-on frontmatter `description`s (~6% less always-loaded context) and the per-skill `references/` resolution note (~40%); every quoted trigger phrase, disambiguation target, and resolution path kept. `sdd-scaffold` wording made imperative per the skill-authoring style.

## [0.3.0] - 2026-07-11

### Added
- Skills: `sdd-review` — opt-in orchestration that dispatches the installed generic reviewers plus `sdd-traceability-auditor` and `sdd-spec-conformance-reviewer`, consolidates the findings, and optionally posts them to the PR (delegates generic review + posting; adds the SDD lenses).
- Agents: `sdd-spec-conformance-reviewer` — read-only, judges whether implemented code satisfies the normative `SPEC §` / `REQ` acceptance criteria it cites, clause by clause.
- References: `references/artefact-prose.md` — the artefact prose-economy rule (one home per fact for commit body / PR body / changelog / review comments; cite identifiers, don't restate).

### Changed
- Skills: `sdd-archive` now archives **inside the implementing PR** (as the final commit of the branch, `implementation: shipped` set there) rather than in a follow-up PR; methodology §9 Definition of Done and the scaffold templates (`development-process.md`, `ai-workflow.md`, `AGENTS.md`) updated to match.
- References: the prose-economy rule is cross-linked from `sdd-methodology.md` §11, the `spec-driven-development` router, `sdd-with-superpowers.md`, and the Cursor rule; scaffolded repos inherit the short form via the templates.
- Agents: modernized `sdd-doc-reviewer` and `sdd-traceability-auditor` descriptions to the prose-summary format (conditions + named trigger scenarios + a "See When to invoke" pointer), replacing the embedded `<example>` block; folded the worked scenario into each agent's `When to invoke` body as prose bullets. `docs/authoring.md` updated to prescribe this form.

## [0.2.1] - 2026-06-18

### Fixed
- Skills: the bundled `references/` lives at the plugin root, but the five skills cited it as a bare `references/…` that a reader resolves relative to the *skill* directory — so the first Read failed on every load (and risked the agent improvising rules rather than grounding in the methodology). Each skill now carries a one-line note that `references/` is plugin-root-relative, with host-agnostic resolution (`${CLAUDE_PLUGIN_ROOT}/references/…`, `../../references/…`, or Glob). `sdd-doc-reviewer` clarified likewise and made self-contained. No change to the single-copy (DRY) design.

## [0.2.0] - 2026-06-18

Consolidated the skill surface and aligned the plugin to **complement the superpowers plugin** — SDD owns the spec / document / traceability layer; the engineering loop (planning, TDD, execution, generic verification, code review, branch-finishing) is deferred to superpowers.

### Changed
- Skills: consolidated **11 → 5**. Merged `sdd-requirement` + `sdd-spec` + `sdd-adr` into `sdd-specify` (the definition layer); refocused `sdd-trace` to own the traceability/drift gate; refocused `sdd-archive` to own the document-side Definition of Done; rewrote `spec-driven-development` as the SDD↔superpowers integration map. Cuts always-on description cost ~33% (~2,385 → ~1,600 tokens) and the `/sdd-*` command surface from 10 to 4.
- Skills / agents / rules / hooks: cross-host hardening — `sdd-scaffold` resolves bundled templates host-agnostically (`${CLAUDE_PLUGIN_ROOT}` with a Glob fallback for Cursor/other installs); `cursor-hooks.json` adds `"version": 1`; thinned `sdd-context.mdc` and the `spec-driven-development` routing table; deduplicated superpowers handoffs in worker skills (one-liners + `references/sdd-with-superpowers.md`).
- Agents: trimmed `sdd-traceability-auditor` and `sdd-doc-reviewer` descriptions to ~1 example (≤~1,000 chars) and moved triggering detail into a `When to invoke` body section; scoped `sdd-doc-reviewer` explicitly to SDD documents (code review is superpowers' `requesting-code-review`).
- Hooks / Cursor rule / docs / scaffold templates: updated `session-start.sh`, `spec-edit-reminder.sh`, `rules/sdd-context.mdc`, `references/templates/*`, and the contributor docs to the new surface and the superpowers handoffs.

### Added
- References: `references/sdd-with-superpowers.md` — the SDD↔superpowers boundary and the `docs/superpowers/*` → canonical-tree (`docs/specifications/`, `docs/plans/`) path redirect.
- References: `references/cross-repo-gap.md` — the cross-repo gap-draft pattern (demoted from the former `sdd-gap` skill).

### Removed
- Skills: `sdd-requirement`, `sdd-spec`, `sdd-adr` (→ `sdd-specify`); `sdd-plan`, `sdd-implement` (→ superpowers' planning / execution / TDD); `sdd-verify` (→ `sdd-trace` + `sdd-archive` + superpowers' `verification-before-completion`); `sdd-gap` (→ `references/cross-repo-gap.md`).

## [0.1.0] - 2026-06-18

First build — a dual-host (Claude Code + Cursor) Spec-Driven Development surface. Pure Markdown + JSON, language-agnostic and config-driven via a `docs/.sdd.yaml` descriptor; no MCP backend.

### Added
- Dual-host manifests (`.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`) with parity-enforced metadata; plugin `name` is `sdd`.
- Skills: `spec-driven-development` — auto-invoked awareness/router; recognises SDD vocabulary, explains the methodology, routes intent to the worker skills, and blocks code-first work when no `REQ`/spec exists. Only its `description` is always-on.
- Skills: the SDD loop/lifecycle set — `sdd-scaffold`, `sdd-requirement`, `sdd-spec`, `sdd-adr`, `sdd-plan`, `sdd-implement`, `sdd-verify`, `sdd-trace`, `sdd-archive`, `sdd-gap`. Each is auto-invoked on intent and user-invocable as `/sdd-*`; all read the `docs/.sdd.yaml` descriptor and operate on Markdown, not source code.
- Agents: `sdd-traceability-auditor` (read-only full-tree drift/orphan scan — the `spec-check` analogue) and `sdd-doc-reviewer` (read-only review of a requirement/spec/ADR/plan for boundary violations). Both declare `tools:` (read-only), never `allowed-tools:`.
- Hooks: host-agnostic `hooks/session-start.sh` (detects an SDD repo, prints context + the `/sdd-*` surface, exits 0) and `hooks/spec-edit-reminder.sh` (after an edit to a requirement/spec/ADR/plan or the traceability map, reminds to sync traceability and run `/sdd-trace`). Wired via `hooks/hooks.json` (Claude, `${CLAUDE_PLUGIN_ROOT}`) and `hooks/cursor-hooks.json` (Cursor, workspace-relative).
- References: `references/sdd-methodology.md` (the universal methodology — document kinds, RFC-2119 discipline, identifiers, traceability chain, two source-of-truth modes, DoR/DoD, anti-patterns), `references/traceability-schema.md` (the `traceability.yaml` record format + the `.sdd.yaml` descriptor schema), and `references/templates/` (the document templates `sdd-scaffold` emits).
- Cursor rule: `rules/sdd-context.mdc` mirroring the `spec-driven-development` router; declared via the Cursor manifest's `rules` path.
- Validation harness: `scripts/validate.py` (manifests, dual-host parity, declared component paths, kebab-case names, hook-config JSON, and skill/agent frontmatter — agents must use `tools:` not `allowed-tools:`) and the `scripts/validate.sh` soft-skip wrapper.
- CI: `.github/workflows/validate.yml` (pins Python, strict in CI).
- Community files under `.github/` (issue templates, PR template, Copilot instructions).
- Docs: `docs/install.md`, `docs/testing.md`, `docs/versioning.md`, `docs/authoring.md`.
