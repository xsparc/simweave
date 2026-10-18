"use strict";
(() => {
  const el = (id) => document.getElementById(id);
  const defaultPolicy = JSON.stringify(
    {
      schema_version: 1,
      metrics: [{ metric: "rmse", max_increase: 0.1 }],
      resamples: 5000,
      random_seed: 1729,
    },
    null,
    2,
  );
  let run = "",
    catalog = "",
    epoch = 0,
    busy = false;
  let job = null,
    generation = null,
    role = null,
    jobAfter = "",
    buildAfter = null;
  const controllers = new Set();
  let pendingApproval = null,
    eventRows = [],
    eventAfter = null,
    decisionAfter = null;
  const show = (id, value) => {
    el(id).textContent =
      typeof value === "string" ? value : JSON.stringify(value, null, 2);
  };
  function controls() {
    for (const button of document.querySelectorAll("button"))
      button.disabled = busy && button.id !== "disconnect";
    for (const id of ["jobs", "builds"]) el(id).disabled = busy;
    el("cancel-job").disabled =
      busy || !job || !["queued", "running"].includes(job.status);
    el("retry-job").disabled =
      busy || !job || job.status !== "failed" || job.attempt >= 5;
    el("download-job").disabled = busy || !job?.artifact;
    el("import-job").disabled =
      busy || role !== "importer" || job?.status !== "succeeded";
    el("upload").disabled = busy || role !== "importer";
    el("compare").disabled =
      busy || role !== "importer" || !generation || !el("builds").value;
    el("more-jobs").disabled = busy || !jobAfter;
    el("more-builds").disabled = busy || buildAfter === null;
    el("promote").disabled =
      busy || role !== "approver" || generation === null || !el("builds").value;
    el("rollback").disabled =
      busy || role !== "approver" || generation === null || !el("events").value;
    el("more-events").disabled = busy || eventAfter === null;
    el("more-decisions").disabled = busy || decisionAfter === null;
    for (const id of ["events", "decisions"]) el(id).disabled = busy;
  }
  function reset() {
    epoch++;
    for (const c of controllers) c.abort();
    controllers.clear();
    run = catalog = "";
    job = generation = role = null;
    jobAfter = "";
    buildAfter = null;
    busy = false;
    pendingApproval = null;
    eventRows = [];
    eventAfter = decisionAfter = null;
    el("approval-dialog").close();
    el("approval-reason").value = "";
    el("policy").value = defaultPolicy;
    show("approval-preview", "");
    show("event-detail", "No approval selected.");
    el("metric-summary").replaceChildren();
    for (const id of ["events", "decisions"])
      el(id).replaceChildren(new Option("Select an item", ""));
    for (const id of [
      "run-token",
      "catalog-token",
      "build-label",
      "bundle",
      "suite-file",
    ])
      el(id).value = "";
    for (const id of ["jobs", "builds"])
      el(id).replaceChildren(new Option("Select an item", ""));
    show(
      "identity",
      "Disconnected. Tokens stay in memory until disconnect or reload.",
    );
    show("job-detail", "No job selected.");
    show("build-detail", "No build selected.");
    show("baseline", "No catalog connected.");
    show("verdict", "No comparison requested.");
    show("comparison-detail", "");
    el("error").hidden = true;
    show("status", "Disconnected; evidence cleared.");
    controls();
  }
  async function request(path, kind, options = {}, binary = false) {
    const credential = kind === "run" ? run : catalog;
    if (!credential) throw new Error(`Connect a ${kind} token first.`);
    const current = epoch,
      controller = new AbortController();
    controllers.add(controller);
    const timer = setTimeout(() => controller.abort(), 60000);
    try {
      const response = await fetch(path, {
        ...options,
        signal: controller.signal,
        headers: {
          Authorization: `Bearer ${credential}`,
          ...(options.body ? { "Content-Type": "application/json" } : {}),
          ...options.headers,
        },
      });
      const data =
        response.ok && binary ? await response.blob() : await response.json();
      if (current !== epoch) throw new Error("Connection changed.");
      if (!response.ok) {
        const detail =
          typeof data.detail === "string"
            ? data.detail
            : "Check the input contract and permissions.";
        const error = new Error(`${response.status}: ${detail}`);
        error.status = response.status;
        throw error;
      }
      return data;
    } finally {
      clearTimeout(timer);
      controllers.delete(controller);
    }
  }
  function action(id, event, operation) {
    el(id).addEventListener(event, async (e) => {
      e.preventDefault();
      if (busy) return;
      const current = epoch;
      busy = true;
      controls();
      el("error").hidden = true;
      show("status", "Working...");
      try {
        await operation();
        if (current === epoch) show("status", "Complete.");
      } catch (error) {
        if (current === epoch) {
          show(
            "error",
            error.name === "AbortError"
              ? "Request timed out. Retry with the same idempotency key if submission was uncertain."
              : error.message,
          );
          el("error").hidden = false;
          show("status", "Action needs attention.");
        }
      } finally {
        if (current === epoch) {
          busy = false;
          controls();
        }
      }
    });
  }
  const pathJob = () => {
    if (!el("jobs").value) throw new Error("Select a job first.");
    return "/api/v1/suite-jobs/" + encodeURIComponent(el("jobs").value);
  };
  const pathBuild = () => {
    if (!el("builds").value) throw new Error("Select a build first.");
    return "/api/v1/catalog/builds/" + encodeURIComponent(el("builds").value);
  };
  function renderJob(item) {
    job = item;
    show("job-detail", item);
    const selected = el("jobs").selectedOptions[0];
    if (selected?.value === item.id)
      selected.textContent = `${item.status} / ${item.id}`;
  }
  async function jobs(after = "") {
    const data = await request(
      `/api/v1/suite-jobs?limit=50&after=${encodeURIComponent(after)}`,
      "run",
    );
    job = null;
    show("job-detail", "Select and inspect a job.");
    el("jobs").replaceChildren(
      new Option("Select a job", ""),
      ...data.items.map((j) => new Option(`${j.status} / ${j.id}`, j.id)),
    );
    jobAfter = data.items.length === 50 ? data.items.at(-1).id : "";
  }
  async function builds(after = 0) {
    el("metric-summary").replaceChildren();
    const overview = await request("/api/v1/catalog", "catalog");
    const data = await request(
      `/api/v1/catalog/builds?limit=50&after=${after}`,
      "catalog",
    );
    generation = overview.generation;
    role = overview.role;
    show(
      "identity",
      `Catalog role: ${role}. Run credential ${run ? "supplied" : "not supplied"}.`,
    );
    show(
      "baseline",
      generation
        ? `Approved baseline: ${overview.active_baseline} / generation ${generation}`
        : "No approved baseline. Comparison is unavailable until an approver promotes one.",
    );
    el("builds").replaceChildren(
      new Option("Select a build", ""),
      ...data.items.map((b) => new Option(b.label, b.label)),
    );
    buildAfter = data.next_after;
    show("build-detail", "Select and inspect a build.");
    show("verdict", "No comparison requested.");
    show("comparison-detail", "");
  }
  async function download(path, kind) {
    const blob = await request(path + "/artifact", kind, {}, true);
    const url = URL.createObjectURL(blob),
      link = document.createElement("a");
    link.href = url;
    link.download = "evidence.zip";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  el("disconnect").addEventListener("click", reset);
  el("access").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (busy) return;
    const r = el("run-token").value.trim(),
      c = el("catalog-token").value.trim();
    reset();
    run = r;
    catalog = c;
    const current = epoch;
    busy = true;
    controls();
    try {
      if (!run && !catalog) throw new Error("Provide a run or catalog token.");
      if (run) await jobs();
      if (catalog) await builds();
      if (current === epoch) {
        show("status", "Connected.");
        if (!catalog)
          show(
            "identity",
            "Run credential connected. Catalog token not supplied.",
          );
      }
    } catch (error) {
      if (current === epoch) {
        reset();
        show("error", error.message);
        el("error").hidden = false;
      }
    } finally {
      if (current === epoch) {
        busy = false;
        controls();
      }
    }
  });
  action("submit", "submit", async () => {
    const source = el("suite").value;
    if (new TextEncoder().encode(source).length > 65536)
      throw new Error("Suite exceeds 64 KiB.");
    const data = await request("/api/v1/suite-jobs", "run", {
      method: "POST",
      headers: { "Idempotency-Key": el("request-key").value },
      body: JSON.stringify(JSON.parse(source)),
    });
    el("jobs").replaceChildren(
      new Option(`${data.status} / ${data.id}`, data.id),
    );
    renderJob(data);
  });
  action("suite-file", "change", async () => {
    const file = el("suite-file").files[0];
    if (!file) return;
    if (file.size > 65536) throw new Error("Suite exceeds 64 KiB.");
    const current = epoch,
      text = await file.text();
    JSON.parse(text);
    if (epoch === current) el("suite").value = text;
  });
  action("refresh-jobs", "click", () => jobs());
  action("more-jobs", "click", () => jobs(jobAfter));
  el("jobs").addEventListener("change", () => {
    job = null;
    show("job-detail", "Inspect the selected job to enable actions.");
    controls();
  });
  action("inspect-job", "click", async () =>
    renderJob(await request(pathJob(), "run")),
  );
  for (const verb of ["cancel", "retry"])
    action(verb + "-job", "click", async () =>
      renderJob(
        await request(pathJob() + "/" + verb, "run", { method: "POST" }),
      ),
    );
  action("download-job", "click", () => download(pathJob(), "run"));
  function labelPath() {
    if (!el("import").reportValidity())
      throw new Error("Provide a valid build label.");
    return (
      "/api/v1/catalog/builds/" + encodeURIComponent(el("build-label").value)
    );
  }
  action("import", "submit", async () => {
    if (!job || job.id !== el("jobs").value)
      throw new Error("Inspect the selected job first.");
    await request(labelPath() + "/from-job", "catalog", {
      method: "POST",
      body: JSON.stringify({
        schema_version: 1,
        job: job.id,
        role: el("build-role").value,
      }),
    });
    await builds();
  });
  action("upload", "click", async () => {
    const file = el("bundle").files[0];
    if (!file || file.size > 128 * 1024 * 1024)
      throw new Error("Choose an evidence ZIP no larger than 128 MiB.");
    await request(labelPath() + "?role=" + el("build-role").value, "catalog", {
      method: "PUT",
      headers: { "Content-Type": "application/zip" },
      body: file,
    });
    await builds();
  });
  action("refresh-builds", "click", () => builds());
  action("more-builds", "click", () => builds(buildAfter));
  el("builds").addEventListener("change", () => {
    el("metric-summary").replaceChildren();
    show("build-detail", "Inspect the selected build.");
    show("verdict", "No comparison requested.");
    show("comparison-detail", "");
    controls();
  });
  action("inspect-build", "click", async () =>
    show("build-detail", await request(pathBuild(), "catalog")),
  );
  action("download-build", "click", () => download(pathBuild(), "catalog"));
  action("compare", "click", async () => {
    pathBuild();
    const result = await request("/api/v1/catalog/comparisons", "catalog", {
      method: "POST",
      body: JSON.stringify({
        schema_version: 1,
        build: el("builds").value,
        generation,
      }),
    });
    show(
      "verdict",
      `${result.statistics.status} / baseline generation ${result.baseline_generation}. Inconclusive is not a pass.`,
    );
    show("comparison-detail", result);
    renderMetrics(result);
  });
  function renderMetrics(result) {
    const container = el("metric-summary");
    container.replaceChildren();
    const heading = document.createElement("p");
    heading.textContent = `${result.candidate_build} versus ${result.baseline_build}, generation ${result.baseline_generation}: ${result.statistics.status}. Inconclusive is not a pass.`;
    container.append(heading);
    for (const group of result.statistics.groups) {
      const title = document.createElement("p");
      title.textContent = `${group.name} / ${group.adapter}: ${group.complete_pairs} complete pairs. ${group.issues.join("; ")}`;
      container.append(title);
      const table = document.createElement("table");
      const header = table.createTHead().insertRow();
      for (const text of [
        "Metric",
        "Mean change",
        "95% interval",
        "Allowed increase",
        "Decision",
      ]) {
        const th = document.createElement("th");
        th.scope = "col";
        th.textContent = text;
        header.append(th);
      }
      const body = table.createTBody();
      for (const metric of group.metrics) {
        const row = body.insertRow(),
          interval = metric.interval;
        for (const value of [
          metric.metric,
          interval?.mean ?? "Unavailable",
          interval ? `${interval.low} to ${interval.high}` : "Unavailable",
          metric.max_increase,
          metric.verdict,
        ]) {
          row.insertCell().textContent = String(value);
        }
      }
      const wrapper = document.createElement("div");
      wrapper.className = "metric-table";
      wrapper.append(table);
      container.append(wrapper);
    }
    const warnings = document.createElement("p");
    warnings.textContent = result.statistics.warnings.join("; ");
    container.append(warnings);
  }
  async function events(after = 0) {
    const data = await request(
      `/api/v1/catalog/events?limit=50&after=${after}`,
      "catalog",
    );
    eventRows = data.items;
    eventAfter = data.next_after;
    el("events").replaceChildren(
      new Option("Select an approval", ""),
      ...eventRows.map(
        (e) =>
          new Option(
            `${e.generation}: ${e.action} / ${e.build}`,
            String(e.generation),
          ),
      ),
    );
    show(
      "event-detail",
      "Select an approval to inspect its policy and audit identity.",
    );
  }
  async function decisions(after = 0) {
    const data = await request(
      `/api/v1/catalog/comparisons?limit=50&after=${after}`,
      "catalog",
    );
    decisionAfter = data.next_after;
    el("decisions").replaceChildren(
      new Option("Select a comparison", ""),
      ...data.items.map((d) => new Option(String(d.id), String(d.id))),
    );
  }
  action("refresh-events", "click", () => events());
  action("more-events", "click", () => events(eventAfter));
  action("refresh-decisions", "click", () => decisions());
  action("more-decisions", "click", () => decisions(decisionAfter));
  el("events").addEventListener("change", () => {
    show(
      "event-detail",
      eventRows.find((e) => String(e.generation) === el("events").value) ||
        "No approval selected.",
    );
    controls();
  });
  action("inspect-decision", "click", async () => {
    if (!el("decisions").value) throw new Error("Select a comparison first.");
    const result = await request(
      "/api/v1/catalog/comparisons/" +
        encodeURIComponent(el("decisions").value),
      "catalog",
    );
    show("comparison-detail", result);
    renderMetrics(result);
  });
  for (const verb of ["promote", "rollback"])
    action(verb, "click", async () => {
      if (role !== "approver" || generation === null)
        throw new Error("Refresh the catalog with an approver token first.");
      if (!el("approval-form").reportValidity())
        throw new Error("Provide a policy and reason.");
      const reason = el("approval-reason").value.trim();
      if (!reason) throw new Error("Provide a visible reason.");
      const body = {
        schema_version: 1,
        expected_generation: generation,
        reason,
      };
      let restored = null;
      if (verb === "promote") {
        pathBuild();
        if (new TextEncoder().encode(el("policy").value).length > 8192)
          throw new Error("Policy exceeds 8 KiB.");
        body.build = el("builds").value;
        body.policy = JSON.parse(el("policy").value);
      } else {
        restored = eventRows.find(
          (e) => String(e.generation) === el("events").value,
        );
        if (!restored) throw new Error("Select an earlier approval first.");
        body.to_generation = restored.generation;
      }
      pendingApproval = { verb, body, epoch };
      show("approval-preview", {
        action: verb,
        ...body,
        ...(restored
          ? { restored_build: restored.build, restored_policy: restored.policy }
          : {}),
      });
      el("approval-dialog").showModal();
      el("cancel-approval").disabled = false;
      el("cancel-approval").focus();
    });
  function cancelApproval() {
    pendingApproval = null;
    el("approval-dialog").close();
    show("approval-preview", "");
  }
  el("cancel-approval").addEventListener("click", cancelApproval);
  el("approval-dialog").addEventListener("cancel", cancelApproval);
  action("confirm-approval", "click", async () => {
    const snapshot = pendingApproval;
    cancelApproval();
    if (!snapshot || snapshot.epoch !== epoch || role !== "approver")
      throw new Error("Approval expired; review it again.");
    try {
      const result = await request(
        "/api/v1/catalog/" + snapshot.verb,
        "catalog",
        { method: "POST", body: JSON.stringify(snapshot.body) },
      );
      await builds();
      await events();
      show("event-detail", result);
      el("approval-reason").value = "";
    } catch (error) {
      if (snapshot.epoch === epoch) generation = null;
      if (error.status === 409)
        throw new Error(
          "Approval rejected: the generation may have changed. Refresh catalog and approval history, review the latest evidence, and confirm again. Nothing is retried automatically.",
        );
      throw error;
    }
  });
  el("approval-form").addEventListener("submit", (event) =>
    event.preventDefault(),
  );
  el("policy").value = defaultPolicy;
  el("suite").value = JSON.stringify(
    {
      schema_version: 1,
      name: "Cart review",
      scenarios: [
        { world: { steps: 300 }, gates: [{ metric: "rmse", threshold: 10 }] },
      ],
      seeds: [1],
      adapters: ["reference"],
      baseline: {},
      candidate: {},
    },
    null,
    2,
  );
  el("request-key").value = crypto.randomUUID();
  controls();
})();
