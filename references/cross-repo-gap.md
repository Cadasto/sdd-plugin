# Cross-repo gap drafts (advanced)

SDD applied to an inter-repo contract. When a repo that practises SDD **consumes a sibling repo that also practises SDD** and hits a missing upstream capability, it doesn't just file an issue — it expresses the need as a **spec draft shaped to drop straight into the upstream's spec tree**, with traceability across the boundary.

This is a niche, advanced pattern (only relevant when `docs/.sdd.yaml` declares an `upstream`). It is documented here rather than as a standalone skill to keep the always-on skill surface lean; `sdd-specify` points here when an upstream gap is in play.

## How to write a gap draft

1. **Write it in the upstream's conventions** — RFC-2119 keywords, `Status: Draft`, cite the existing upstream `REQ` it extends, a one-paragraph rationale rooted in **concrete consumer usage**, explicit acceptance criteria, and out-of-scope. Mirror the upstream's identifier style and section layout, *not* the consumer's. The draft must read as if authored in the upstream repo — that is what makes it droppable.
2. **Store it locally.** A gap draft is `kind: upstream`. It lives under the relation's `gap_drafts`
   directory — `docs/<name>-gap-drafts/<PREFIX>-GAP-NN-<slug>.md` — so the consumer keeps a record, and it
   is emitted from `references/templates/gap-draft.md`. Number sequentially.
3. **Track the lifecycle** in the draft's frontmatter, in `state:` — not `status:`, because the lifecycle
   being tracked is the upstream's:

   | `state` | What moves a draft to it |
   |---|---|
   | `proposed` | The draft is written and numbered. Nothing is filed upstream yet. |
   | `submitted` | The ask is filed upstream; the frontmatter carries the upstream pull request or issue. |
   | `landed-upstream` | Upstream merged it. This repository has not adopted the new surface yet. |
   | `landed` | This repository consumes the new surface and the local workaround is gone. |
   | `rejected` | Upstream declined it, or the draft is withdrawn; the frontmatter says why. |

## Guardrails

- **Speak the upstream's language** — don't impose the consumer's identifier scheme.
- **Rationale from real usage** — ground the need in a concrete consumer scenario, not a hypothetical.
- **One capability per draft** — the same single-concept discipline as a requirement.
- **Keep the local record current** — move the draft's `state:` on as its upstream fate resolves; a stale gap-drafts folder is its own drift.

## Two rules

- **Disclosure** — an upstream artefact names no consumer. The draft states the capability and the
  behaviour it needs, and grounds it in a usage scenario. It does not name who is asking, or what they
  are building.
- **Behaviour preservation** — a dependency bump may be split from adopting its new surface only while
  the workaround it replaces keeps producing the same answers; an unconsumed surface that fails this test
  does not get to wait.

## Declaring the relation

`docs/.sdd.yaml` names the relations this repository has:

```yaml
upstream:
  <name>:
    repo: <module path or URL>
    role: consumed | platform-context | ground-truth
    authority: upstream-leads | local-leads
    gap_drafts: docs/<name>-gap-drafts     # role: consumed only
```

The scalar form — `upstream: "<repo>"` — still means one relation named `upstream` with `role: consumed`.
