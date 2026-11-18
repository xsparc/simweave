# Identity record check

```sh
simweave sweep-bundle-identity-check identity.json
python examples/portable_review.py review-demo
```

The check command reads at most 4097 bytes and rejects records above 4096 bytes.
It reuses the closed identity reader, including duplicate rejection, strict version
and size types, digest syntax and encoding/interpretation constants. It never opens
a bundle or runs a simulator. Success is fixed JSON with schema_version 1,
valid true and interpretation identity_record_validity_only. Errors use the existing
sanitized CLI error boundary and exit 2. No path, record content or digest is echoed.

A valid record need not match any existing bundle: use the existing bundle --identity
gate to check that relationship. The synthetic portable workflow now validates its
retained identity and rejects a separate malformed duplicate-field record without
changing either file. Existing identity schema and export bytes are unchanged.
