<!-- Template: the one document that binds code on the informative profile. Delete this comment. -->
---
kind: constitution
---
# Architecture

What every change in this repository must respect. Each sentence below with MUST or MUST NOT binds;
everything else in `docs/` describes and does not bind. Amend this file only through `/sdd-specify`,
with the reason in the commit body or an ADR.

## Boundaries
- <e.g. The transport package MUST be the only place that builds a request URL.>

## Contracts
- <e.g. A public operation MUST NOT succeed partially: it completes, or it changes nothing.>

## Data
- <e.g. Personal data MUST NOT appear in log lines or error strings.>

## Known gaps
- <what the architecture does not yet settle; one line each>
