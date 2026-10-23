# Offline HTML sweep reports

Status: accepted for implementation, 2026-10-23.

## Decision

Add opt-in `sweep-review --format html`; JSON remains the default. Render only after the existing summarize operation revalidates and binds the sweep and suite report. Preserve exit codes, point ordering, seeds, warnings, counts and whole-point metric withholding for incomplete execution. Display descriptive baseline/candidate means and paired delta mean/minimum/maximum to six significant digits; JSON retains full precision. Include normalized evidence hashes. Escape every source-derived text value. The standalone document contains fixed hash-authorized CSS, no JavaScript or external assets, and a restrictive CSP. Existing CLI input caps and exclusive output creation remain in force.

## Acceptance

Escaped hostile titles produce no executable tags or event attributes; CSP matches fixed CSS; metric values and evidence hashes match validated summaries; incomplete points withhold metrics; CLI validates before writing and refuses overwrite.

## Limits

This is a derived descriptive report, not statistical inference, automatic optimization, baseline approval, signature authentication, raw telemetry validation or cross-engine accuracy proof. CSP is defense in depth; escaping is the primary HTML boundary. No browser or UI dependency enters simulation math. Very large accepted reports can be long; tables scroll horizontally on narrow screens.

