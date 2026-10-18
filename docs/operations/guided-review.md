# Guided baseline review

Open the suite workspace and connect an operator-provisioned catalog token.
Importers retain evidence and create comparisons. Readers and approvers can open
recorded comparisons, inspect metric summaries and browse approval history.
Approvers cannot import or create comparisons; importer permission does not allow
approvals. Run credentials do not provide catalog permission.

To promote, select and inspect a build, review recorded decisions, enter the full
versioned decision policy and a reason, then choose **Review promotion**. Check the
build, expected generation, thresholds, resampling policy and reason in the dialog.
Cancel is focused initially. Only **Confirm baseline change** submits the request.
Promotion is an explicit human decision; an inconclusive or passing statistic does
not authorize it. The starting policy is an editable example, not a recommendation
for every experiment. Metric changes and tolerances use the metric's original units.

To roll back, refresh approval history, select an earlier event and inspect its
policy, enter a reason, then review and confirm. Rollback appends a new event with
the authenticated identity and restores the exact earlier build and policy. It
does not erase intermediate events. History and comparisons use pages of 50.

On conflict or uncertain response, inspect the latest catalog/history before
retrying. A write may already have committed even if its response was lost.
The browser disables further approval until catalog refresh; it never retries
automatically. Refreshing discards the build selection so review must be deliberate.
Disconnect clears credentials, pending confirmation, history and metrics. Existing
server access controls and maintenance fencing apply to every write.
