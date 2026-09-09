<!-- Template: a cross-repo gap draft — one capability this repository needs from an upstream it
     consumes. Filename: docs/<relation>-gap-drafts/<PREFIX>-GAP-NN-<slug>.md, numbered sequentially.
     Write it in the UPSTREAM's conventions and identifier style, so it drops straight into their
     spec tree. One capability per draft. Move `state:` on as the upstream fate resolves. -->
---
kind: upstream
id: <PREFIX>-GAP-NN
title: <short capability name, in the upstream's words>
state: proposed          # proposed | submitted | landed-upstream | landed | rejected
upstream: <relation name, as declared under `upstream:` in docs/.sdd.yaml>
submitted: <URL, once submitted>
---

<!-- sdd-check: allow rfc2119 -->

# <PREFIX>-GAP-NN — <capability name>

## Ask

<!-- The upstream's conventions apply here: RFC-2119 force, their section layout, their identifier
     style. Keywords are allowed in this document because it is the draft of an upstream
     specification — that is what the waiver above is for. Cite the upstream section this extends. -->

<Extends: the upstream section this builds on, in the upstream's own citation form.>

<The behaviour asked for, stated as the upstream would state it: what the implementation MUST do,
what it SHOULD do, and what it MAY leave open.>

## Rationale from consumer usage

<One paragraph grounded in a concrete usage scenario: what is being attempted, what the current
surface makes impossible or unsafe, and what the workaround costs. A real scenario, not a
hypothetical — and no consumer named.>

## Acceptance criteria

- [ ] <observable condition that proves the capability is delivered upstream>
- [ ] <the negative space: an input or state the capability refuses or fails closed on, with the
      intended failure behaviour as an observable outcome>
- [ ] <…>

## Out of scope

- <what this ask deliberately does not cover, so the upstream can size it>

## Behaviour-preservation test

A dependency bump is split from adopting the new surface only while the workaround it replaces keeps
producing the same answers. An unconsumed surface that fails this test does not get to wait.

<State which side of that test this draft sits on, and what the local workaround is until it lands.>

<!-- An upstream artefact names no consumer. State the capability and the behaviour needed, and ground
     it in a usage scenario — never who is asking, or what they are building. -->
