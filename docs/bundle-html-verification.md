# Bundle HTML verification and portable review

```sh
simweave sweep-bundle-verify-html bundle.json review.html --before before.json --after after.json --identity identity.json
python examples/portable_review.py review-demo
```

HTML verification revalidates the retained bundle and compares exact UTF-8 bytes
with the existing v2 renderer. Optional --before/--after must appear together;
--identity and --expected-sha256 are mutually exclusive and compose with source
checks. No source options preserves standalone bundle verification. Bundle intake
is 192 KiB, each plan and HTML is 64 KiB, identity records are 4096 bytes.
Edits to markup, CSP, styles, encoding or newlines fail rather than being repaired.
Success returns fixed JSON and exit 0; failure uses existing fixed diagnostics
and exit 2. Inputs are never rewritten; no browser or simulator is invoked.

The executable example requires a new destination directory. It creates synthetic
reference plans, retains a bundle and identity, renders source-checked HTML/CSV,
verifies both exports, rejects output collisions and replacement evidence with
matching replacement identity, and checks original input bytes. A simulation
execution guard covers the workflow. It emits a fixed acceptance summary.

Exact rendering depends on renderer version and is not semantic browser equivalence.
A matching identity is not a signature, authorship or independent source evidence.
Retain independent plans and identity targets when substitution detection matters.
