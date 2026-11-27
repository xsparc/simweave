# Independent portable review example

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

To check both retained exports as one local operation, use:

```sh
simweave sweep-bundle-verify-exports bundle.json review.html review.csv \
  --before before.json --after after.json --identity identity.json
```

This reads and verifies a single bundle against both exact exports, with at
most one successful verification response. A mismatch in either export
returns exit 2 with no success response and does not change any files. Supply
both source paths or omit both. Use an independently retained identity record
as shown, an independently retained digest via `--expected-sha256`, or
neither. Existing single-export commands and the verification response schema
are unchanged. This check is local consistency, not authorship attestation or
proof of a simulation run.

For scripts that need to distinguish failures, add `--diagnostics` to the paired
command. A failed check exits 2 and writes one JSON object to stderr, such as
`{"schema_version": 1, "error": "verification_failed", "stage": "csv"}`.
Stages are fixed: `bundle`, `identity`, `sources`, `html`, `csv`. Only the
first failed stage is reported. The stage describes which check failed, not
whether its input was missing, invalid, oversized, or inconsistent. Diagnostics
omit filenames, exception details and input contents. Success output and the
default error behavior are unchanged. CLI syntax errors are handled separately.
