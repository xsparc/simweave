# Review and reproduce CI evidence

Every completed `simweave suite` writes `report.html`, `evidence.zip`, and
`environment.json` alongside its JSON/JUnit reports and full recordings. These
artifacts are written for passing suites, failed gates, and per-case execution
errors. Interruptions and storage failures can still leave incomplete output.

## Review in a browser

Download the CI artifact, unpack it, and open `report.html` in a browser with
JavaScript enabled. The document contains its own data, CSS, and script; it needs
no SimWeave installation, API token, running service, simulator, or external CDN.
Browser restrictions on local HTML may vary; direct file-open remains an explicit
validation gap in the current [validation record](../governance/evidence-validation.md).

The first failing pair is selected automatically. Read the candidate's **NEW
FAILURE** and regression gates, inspect metric changes and overlaid trajectories,
then choose **Export selected pair**. **Save JSON file** downloads the prepared
export. If a browser blocks downloads, the same JSON is visible for selection and
copying. Changing the selected pair clears an old export to prevent stale evidence.
**Next failure** cycles through failed gates and execution errors. **Next failed
gate** moves keyboard focus to the next failure.

The pair export preserves suite inputs, selected comparison, identifiers, and
runtime metadata. It is a summary, not full telemetry or a runnable bundle.
Reports plot at most 101 points per run; a short transient may be absent from the
plot. No numerical change is labeled statistically significant.

To convert an older suite report:

```sh
simweave report results/report.json --output review.html
```

Conversion validates the report but cannot reconstruct its original runtime;
provenance is shown as unknown. It never overwrites an existing output file.

## Check the complete bundle

```sh
simweave bundle-check results/evidence.zip
```

This command checks the closed v1 manifest, exact member set, SHA-256 checksums,
scenarios/results, complete telemetry, gates, and preview fidelity. It prints
recording/error counts and recorded environment metadata. Exit 0 means integrity
checks passed, even if the original experiment failed quality gates; invalid
bundles return 2. Execution-error cases are explicit and have no complete
recording in the ZIP; partial telemetry remains in the original case directory.

The v1 format permits only ordinary single-disk ZIP, stored/deflated entries,
no archive comment, at most 194 members, 64 KiB of central directory and manifest,
4 MiB for report JSON, 16 MiB per other member, and 128 MiB total compressed or
uncompressed data. Readers never extract archive paths or execute its content.
The manifest and metadata are unsigned: checksums detect inconsistency, not a
malicious producer who replaces both content and checksums.

## Record and retain a reproducible image

Build a trusted image containing the desired SimWeave source and all adapters.
The supplied ROS image includes reference, MuJoCo, and Gazebo. This POSIX shell
example records the exact local Docker image ID and the checked-out source commit:

```sh
docker build -f integrations/ros2/Dockerfile -t simweave:evidence .
image_id=$(docker image inspect --format '{{.Id}}' simweave:evidence)
revision=$(git rev-parse HEAD)
docker run --name evidence-original --network none --pids-limit 256 --memory 4g --cpus 2 \
  "$image_id" simweave suite examples/cart-regression.json --output /tmp/results \
  --source-revision "$revision" --image-id "$image_id"
# Collect even when the suite returns 1 (quality failure) or 2 (execution errors).
docker cp evidence-original:/tmp/results results
docker rm evidence-original
docker image save --output simweave-runtime.tar "$image_id"
```

PowerShell operators can use `$imageId = docker image inspect --format '{{.Id}}'
simweave:evidence` on one line and `$revision = git rev-parse HEAD`. The resulting
image ID has the form `sha256:` followed by 64 hexadecimal characters; it is the
immutable local ID reported by the installed Docker engine. Use exactly its
`.Id` value; do not substitute a mutable tag or a `RepoDigests` entry.
Keep the image archive separately with the evidence. On another machine, use
`docker image load --input simweave-runtime.tar` from a trusted source. Images are
not automatically pulled, published, or included in the small evidence bundle.
CI retains reports/bundles for seven days; ephemeral CI images require a separate
operator-approved retention process to support later reruns.

The revision/image fields are explicitly supplied assertions. Use a clean checkout
and the ID of the image actually executing the suite; unknown values stay null.
The runtime fingerprint independently records installed Python source bytes,
Python version, OS family, architecture, and a fixed dependency-version list.
Native dependencies are preserved by retaining the exact image. No host name,
account name, filesystem location, token, or environment-variable inventory is
collected. Scenario names and parameters are intentionally included; review them
before sharing an artifact.

## Rerun in a clean container

With the original trusted image installed locally, one command reruns the suite:

```sh
simweave rerun results/evidence.zip --image sha256:YOUR_64_HEX_IMAGE_ID --output rerun-results
```

Supply the full ID reported by Docker, not the placeholder above. The selected ID
must equal the recorded ID. Bundles with unknown image identity can be reviewed
and verified but cannot use this exact-image rerun command. A native-host bundle
cannot be converted into container provenance after the fact; rerun the original
suite in a trusted container to establish a new recording.

The command validates input before creating a container, uses no network or host
mounts, runs as UID/GID 10001 with dropped capabilities and no-new-privileges,
caps CPU/memory/processes, and invokes the image's installed fixed CLI. It does
not execute source or scripts from the bundle. The trusted image's entrypoint
must support `python -m simweave.cli` (the supplied images do). The child compares
installed code/runtime fingerprints before simulation. Temporary container state
is removed on completion or failure; output directories are never overwritten.
The one-hour execution deadline fails explicitly if a large suite takes too long.

`reproduction.json` distinguishes:

- `reproduced` / exit 0: every complete result and telemetry digest matches,
  including any original failed quality gates. Original and rerun suite exit codes
  remain visible; successful reproduction does not mean the controller passed.
- `different` / exit 1: compatible fingerprint, but numerical/result differences.
- `environment_mismatch` / exit 2: fingerprint differs; no simulation was executed.
- `incomplete` / exit 2: original or rerun execution errors prevent full comparison.

Invalid input, unavailable Docker/image, storage errors, or container failures
return 2 without claiming reproduction. Matching software and image IDs are not
a guarantee of identical hardware/kernel behavior. Actual full-resolution
telemetry comparison is the verdict. No cross-engine equality claim is made.
