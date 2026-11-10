# Source checked bundle rendering

Bundle rendering can now require explicit before/after source plans in the same invocation as retained identity verification.

```sh
simweave sweep-bundle-render bundle.json --format html --before before.json --after after.json --identity identity.json --output review.html
simweave sweep-bundle-render bundle.json --format csv --before before.json --after after.json --output review.csv
```

The optional --before and --after arguments must appear together. The command strictly reads both plans and recomputes the bundle through the existing source verifier. A matching identity or expected digest does not bypass this source gate. Partial pairs, wrong sources with matching identity, reversal and consistent replacement all fail before exclusive HTML/CSV creation.

Existing limits remain: bundle 192 KiB; each plan and rendered output 64 KiB; identity record 4096 bytes. Existing calls without sources preserve their behavior. Input files are read-only, existing output files are never overwritten, and failures use fixed diagnostics with exit 2. Success returns 0. No simulation or evidence repair occurs; renderer layouts and CSV bytes are unchanged.

Retain plans and identity targets independently. Source consistency is not authorship, provenance or observed simulation equivalence. The portable example tests exercise both render formats with the source and identity gates together.
