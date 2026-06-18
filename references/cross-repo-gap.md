# Cross-repo gap drafts (advanced)

SDD applied to an inter-repo contract. When a repo that practises SDD **consumes a sibling repo that also practises SDD** and hits a missing upstream capability, it doesn't just file an issue — it expresses the need as a **spec draft shaped to drop straight into the upstream's spec tree**, with traceability across the boundary.

This is a niche, advanced pattern (only relevant when `docs/.sdd.yaml` declares an `upstream`). It is documented here rather than as a standalone skill to keep the always-on skill surface lean; `sdd-specify` points here when an upstream gap is in play.

## How to write a gap draft

1. **Write it in the upstream's conventions** — RFC-2119 keywords, `Status: Draft`, cite the existing upstream `REQ` it extends, a one-paragraph rationale rooted in **concrete consumer usage**, explicit acceptance criteria, and out-of-scope. Mirror the upstream's identifier style and section layout, *not* the consumer's. The draft must read as if authored in the upstream repo — that is what makes it droppable.
2. **Store it locally** under a gap-drafts area, e.g. `docs/<upstream>-gap-drafts/SDK-GAP-NN-<slug>.md`, so the consumer keeps a record. Number sequentially.
3. **Track the lifecycle** in the draft's frontmatter:

   | State | Folder | Marker |
   |---|---|---|
   | Proposed | gap-drafts root | open |
   | Submitted upstream | (stays) | `Upstream: <PR/issue URL>` in frontmatter |
   | Landed | `landed/` | quote-block citing the upstream `REQ`/commit that closed it |
   | Rejected / withdrawn | `rejected/` | quote-block stating why |

## Guardrails

- **Speak the upstream's language** — don't impose the consumer's identifier scheme.
- **Rationale from real usage** — ground the need in a concrete consumer scenario, not a hypothetical.
- **One capability per draft** — the same single-concept discipline as a requirement.
- **Keep the local record current** — move the draft through `landed/` / `rejected/` as its upstream fate resolves; a stale gap-drafts folder is its own drift.
