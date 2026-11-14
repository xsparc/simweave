# Identity file export

```sh
simweave sweep-bundle-identity bundle.json --output identity.json
python examples/portable_review.py review-demo
```

Omitting --output preserves the existing stdout JSON record. With --output, the
same version-1 identity record is serialized as pretty UTF-8 JSON plus LF and
validated against the existing closed reader and 4096-byte bound before exclusive
creation. Successful file export has no stdout. Invalid bundles and existing output
paths fail without replacing retained evidence. The portable synthetic example now
uses this CLI export for original and replacement identities. No simulation runs.
Identity is normalized content identity, not a signature or original-file hash.
