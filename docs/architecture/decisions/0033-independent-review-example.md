# ADR 0033: Independent review example

Status: accepted
Date: 2026-11-13

## Decision


```sh
python examples/portable_review.py review-demo
```

Choose a new destination directory. The existing synthetic reference-plan workflow
now supplies the independently retained before/after plans during both HTML and
CSV verification. It checks that edited copies fail without repair and that a
replacement bundle with its matching identity and canonical exports passes
standalone verification but fails against the original plans.

The workflow retains original source, bundle, identity and export bytes and checks
they remain unchanged. Tampered and replacement fixtures use distinct files. The
simulation guard covers the entire workflow. Fixed success output is unchanged;
failures emit a sanitized acceptance category. CLI contracts, limits and renderer
bytes are unchanged. Source consistency and retained identity do not authenticate
authorship or demonstrate simulation equivalence.

## Alternatives and acceptance

Reuse existing validators and exact renderers. Exclusive creation avoids replacing retained evidence. Acceptance covers independent source checks, replacement evidence, collisions, bounds, byte preservation and non-execution. No runtime authority or renderer-layout changes.
