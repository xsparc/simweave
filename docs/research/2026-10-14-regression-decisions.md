# Accepted research: regression decisions

DirectionBriefV1, schema version 1. Baseline commit:
`a2337c1e4bfdbeb8de332efc494e456d3d174cdc`. Scanned 2026-10-14.
Coverage: paired statistical inference, deterministic computation, transactional
baseline history, CI evidence retention. The maintainer accepted these two
directions; ADR 0005 records their bounded implementation.

1. **Paired uncertainty and practical thresholds — adopt.**
   [SciPy's bootstrap reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
   describes paired resampling, percentile intervals, RNG control and degenerate
   data caveats. Its live documentation is undated (checked on the scan date).
   Confidence: high in method semantics, medium in applicability to operational
   workloads. Alignment: portable, inspectable decisions. Opportunity: distinguish
   noisy changes from practical regressions. Risk: dependence, small samples,
   percentile coverage and repeated testing. Cost: medium. Roadmap delta: pure
   bounded mean-difference analysis with explicit assumptions. Verify against
   exact small distributions, known shifts, degeneracy, and 30-seed native runs.
   [Python's reproducibility notes](https://docs.python.org/3.12/library/random.html#notes-on-reproducibility)
   support a private seeded generator; record the algorithm/runtime rather than
   promise arbitrary future-version numerical identity.

2. **Immutable approval history — adopt.**
   [SQLite transactions](https://www.sqlite.org/lang_transaction.html) (updated
   2026-02-18) describe one writer, immediate transactions, and stable read
   snapshots. Confidence: high. Alignment: portable single-host stewardship.
   Opportunity: atomic append-only approval events with stale-generation checks;
   risk: local database access is not identity or tamper-proof authorization.
   Cost: medium. Roadmap delta: bounded local catalog and explicit promotion /
   rollback, with portable exports. Verify competing promotions, restart, immutable
   records and 20 candidate builds against one pinned approval event.

[GitHub workflow artifacts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts)
(undated, checked 2026-10-14) are retained workflow outputs, not a permanent baseline
authority. Preserve original bundles separately from the derived catalog. Overall
recommendation: implement the accepted pair together. Evidence gaps: representative
seed populations, empirical interval coverage, human approval studies, hosted
identity, permanent artifact storage and independent provenance authentication.
