---
name: sdd-gap
description: This skill should be used when the user asks to "this dependency is missing X", "draft a spec for the upstream repo", "file a gap against the SDK/library we consume", or "express a needed upstream capability as a spec delta". Writes a spec draft in the upstream repo's own conventions and tracks it through proposed → submitted → landed/rejected. Only relevant when this repo consumes a sibling repo that also uses SDD (see .sdd.yaml `upstream`).
argument-hint: "<the missing upstream capability>"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Gap draft — SDD across a repo boundary (advanced)

When this repo hits a missing capability in a sibling repo it consumes, don't just file an issue — express the need as a **spec draft shaped to drop straight into the upstream's spec tree**, with full traceability across the boundary. Read `docs/.sdd.yaml` for `upstream`; if it is blank, this repo declares no SDD upstream — confirm with the user before proceeding.

## Steps

1. **Write the draft in the upstream's conventions** — RFC-2119 keywords, `Status: Draft`, cite the existing upstream `REQ` it extends, a one-paragraph rationale rooted in **concrete consumer usage**, explicit acceptance criteria, and out-of-scope. Mirror the upstream's identifier style and section layout, not this repo's.
2. **Store it locally** under a gap-drafts area (e.g. `docs/<upstream>-gap-drafts/SDK-GAP-NN-<slug>.md`) so the consumer keeps a record. Number sequentially.
3. **Track the lifecycle** in the draft's frontmatter:

   | State | Folder | Marker |
   |---|---|---|
   | Proposed | gap-drafts root | open |
   | Submitted upstream | (stays) | `Upstream: <PR/issue URL>` in frontmatter |
   | Landed | `landed/` | quote-block citing the upstream `REQ`/commit that closed it |
   | Rejected / withdrawn | `rejected/` | quote-block stating why |

4. **Report** the draft path and the suggested submission target.

## Guardrails

- **Speak the upstream's language.** The draft must read as if authored in the upstream repo — that is what makes it droppable. Don't impose this repo's identifier scheme.
- **Rationale from real usage.** Ground the need in a concrete consumer scenario, not a hypothetical.
- **One capability per draft.** Same single-concept discipline as a requirement.
- **Keep the local record current.** Move the draft through `landed/`/`rejected/` as its upstream fate resolves; a stale gap-drafts folder is its own drift.

## Reference

- `references/sdd-methodology.md` — the cross-repo gap loop; §3 boundary rules (the draft is still a requirement+spec, kept in its lane).
