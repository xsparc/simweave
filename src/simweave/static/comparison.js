"use strict";
(() => {
  let epoch = 0, current = null, suite = null, source = "", gateIndex = -1;
  const byId = (id) => document.getElementById(id);
  const number = (value) => value !== 0 && Math.abs(value) < 0.0001
    ? Number(value).toExponential(3)
    : Number(value).toLocaleString(undefined, { maximumSignificantDigits: 7 });
  const show = (message, error = false) => {
    byId("comparison-source").textContent = message;
    byId("comparison-source").classList.toggle("danger", error);
  };
  function clear() {
    current = null;
    gateIndex = -1;
    byId("comparison-content").hidden = true;
    byId("comparison-status").textContent = "SELECT TWO RUNS";
    byId("comparison-status").className = "status neutral";
  }
  function resetSuite() {
    suite = null;
    byId("suite-pair-control").hidden = true;
    byId("next-failed-pair").hidden = true;
  }
  document.addEventListener("workspace-reset", () => {
    epoch++;
    clear(); resetSuite();
    for (const id of ["comparison-baseline", "comparison-candidate"]) {
      byId(id).replaceChildren(new Option("Select a completed run", ""));
    }
    byId("suite-report").value = "";
    byId("suite-report").disabled = true;
    byId("compare-runs").disabled = true;
    show("Connect your workspace to compare runs or open a report.");
  });
  document.addEventListener("workspace-connected", () => {
    byId("suite-report").disabled = false;
    byId("compare-runs").disabled = false;
    show("Select a baseline and candidate, or open a suite report.");
  });
  for (const id of ["comparison-baseline", "comparison-candidate"]) byId(id).addEventListener("change", () => {
    epoch++; clear(); resetSuite(); show("Selection changed. Compare runs to load the new pair.");
  });
  document.addEventListener("runs-changed", (event) => {
    for (const id of ["comparison-baseline", "comparison-candidate"]) {
      const select = byId(id), value = select.value;
      // Keep explicit selections when normal history polling changes the visible page.
      const selectedOption = select.selectedOptions[0]?.cloneNode(true);
      select.replaceChildren(new Option("Select a completed run", ""));
      for (const run of event.detail.filter((run) => run.status === "succeeded")) {
        select.add(new Option(`${run.scenario.name} · ${run.scenario.adapter} · seed ${run.scenario.seed} · ${run.id.slice(0, 8)}`, run.id));
      }
      if (value && ![...select.options].some((o) => o.value === value)) select.add(selectedOption);
      select.value = value;
    }
  });
  byId("comparison-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const request = ++epoch;
    clear(); resetSuite();
    const baseline = byId("comparison-baseline").value, candidate = byId("comparison-candidate").value;
    show("Verifying recordings and comparing runs…");
    try {
      const data = await (await api(`/api/v1/comparisons?baseline=${encodeURIComponent(baseline)}&candidate=${encodeURIComponent(candidate)}`)).json();
      if (request !== epoch) return;
      source = `Workspace recordings · baseline ${baseline} · candidate ${candidate}`;
      render(data);
      show("Recorded telemetry integrity checked. Controller differences and gate outcomes are shown below.");
    } catch (error) {
      if (request === epoch) show(error.message, true);
    }
  });
  byId("suite-report").addEventListener("change", async () => {
    const request = ++epoch;
    clear(); resetSuite();
    const file = byId("suite-report").files[0];
    if (!file) return;
    show("Validating suite report…");
    try {
      if (file.size > 4 * 1024 * 1024) throw new Error("Suite report exceeds 4 MiB.");
      const body = await file.text();
      if (request !== epoch) return;
      const data = await (await api("/api/v1/suite-reports/compare", { method: "POST", body })).json();
      if (request !== epoch) return;
      suite = data;
      byId("suite-pair").replaceChildren();
      data.pairs.forEach((pair, index) => byId("suite-pair").add(new Option(
        `${pair.name} · ${pair.adapter} · seed ${pair.seed} · ${pair.error ? "ERROR" : pair.comparison.passed ? "PASS" : "FAIL"}`, index,
      )));
      byId("suite-pair-control").hidden = false;
      byId("next-failed-pair").hidden = !data.pairs.some((p) => p.error || !p.comparison.passed);
      byId("suite-pair").value = String(Math.max(0, data.pairs.findIndex((p) => p.error || !p.comparison.passed)));
      renderPair();
    } catch (error) {
      if (request === epoch) show(error.message, true);
    }
  });
  function renderPair() {
    const pair = suite?.pairs[Number(byId("suite-pair").value)];
    clear();
    if (!pair) return;
    source = `Imported suite ${suite.name} · ${suite.suite_digest} · ${pair.baseline_id} → ${pair.candidate_id}`;
    show(`${suite.name} · ${suite.pairs.length} pairs · suite ${suite.exit_code === 0 ? "PASS" : suite.exit_code === 1 ? "FAIL" : "ERROR"}. Imported summaries are not recording verification.`);
    if (pair.error) {
      byId("comparison-status").textContent = "EXECUTION ERROR";
      byId("comparison-status").className = "status bad";
      show(`${source}. ${pair.error}. Inspect the case artifacts; no complete comparison is available.`, true);
      return;
    }
    render(pair.comparison);
  }
  byId("suite-pair").addEventListener("change", renderPair);
  byId("next-failed-pair").addEventListener("click", () => {
    if (!suite) return;
    const start = Number(byId("suite-pair").value);
    for (let offset = 1; offset <= suite.pairs.length; offset++) {
      const index = (start + offset) % suite.pairs.length, pair = suite.pairs[index];
      if (pair.error || !pair.comparison.passed) {
        byId("suite-pair").value = String(index); renderPair(); break;
      }
    }
  });
  function render(data) {
    current = data; gateIndex = -1;
    byId("comparison-content").hidden = false;
    byId("comparison-setup").textContent = ["baseline", "candidate"].map((role) => {
      const c = data[role].scenario.controller;
      return `${role === "baseline" ? "Baseline" : "Candidate"}: kp ${number(c.kp)}, kd ${number(c.kd)}, force limit ${number(c.max_force)} N`;
    }).join(" · ");
    byId("comparison-status").textContent = data.passed ? "GATES PASS" : "GATES FAIL";
    byId("comparison-status").className = `status ${data.passed ? "good" : "bad"}`;
    byId("comparison-warnings").textContent = data.warnings.join(" ");
    byId("comparison-metrics").replaceChildren();
    data.metrics.forEach((metric) => {
      const row = document.createElement("tr");
      [metric.metric, number(metric.baseline), number(metric.candidate), `${metric.delta > 0 ? "+" : ""}${number(metric.delta)}`].forEach((text) => {
        const cell = document.createElement("td"); cell.textContent = text; row.append(cell);
      });
      byId("comparison-metrics").append(row);
    });
    byId("comparison-gates").replaceChildren();
    const gate = (text, failed) => {
      const line = document.createElement("p");
      line.textContent = text; line.tabIndex = -1;
      line.className = failed ? "failed" : "passed";
      byId("comparison-gates").append(line);
    };
    for (const role of ["baseline", "candidate"]) data[role].result.gates.forEach((g, index) => {
      const newly = role === "candidate" && data.newly_failing_gates.includes(index);
      gate(`${role === "baseline" ? "Baseline" : "Candidate"} · ${g.passed ? "PASS" : newly ? "NEW FAILURE" : "FAIL"} · ${g.metric} ${g.op === "lte" ? "≤" : "≥"} ${number(g.threshold)} · observed ${number(g.value)}`, !g.passed);
    });
    data.regression_gates.forEach((g) => gate(`Regression · ${g.passed ? "PASS" : "FAIL"} · ${g.metric} increase ≤ ${number(g.max_increase)} · observed ${number(g.increase)}`, !g.passed));
    byId("next-failed-gate").disabled = !byId("comparison-gates").querySelector(".failed");
    drawComparison(data);
  }
  function drawComparison(data) {
    const points = [...data.baseline.trajectory, ...data.candidate.trajectory];
    const target = data.baseline.scenario.controller.target;
    const low = Math.min(0, target, ...points.map((p) => p.position));
    const high = Math.max(1, target, ...points.map((p) => p.position));
    const padding = Math.max((high - low) * 0.12, 0.1), min = low - padding, max = high + padding;
    const duration = data.baseline.scenario.world.steps * data.baseline.scenario.world.timestep;
    const x = (time) => 44 + time / duration * 656, y = (value) => 236 - (value - min) / (max - min) * 206;
    byId("comparison-grid").replaceChildren();
    for (let i = 0; i < 5; i++) {
      const value = max - (max - min) * i / 4;
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", "3"); text.setAttribute("y", String(y(value) + 3)); text.textContent = number(value);
      byId("comparison-grid").append(text);
    }
    for (const role of ["baseline", "candidate"]) byId(`${role}-trajectory`).setAttribute("points", data[role].trajectory.map((p) => `${x(p.time)},${y(p.position)}`).join(" "));
    byId("comparison-target").setAttribute("y1", String(y(target)));
    byId("comparison-target").setAttribute("y2", String(y(target)));
    byId("comparison-axis").textContent = `SIMULATION TIME / S     0 → ${number(duration)}`;
    byId("comparison-chart").setAttribute("aria-label", `Baseline and candidate position in metres, 0 to ${number(duration)} seconds. See the metric and gate tables for numeric changes.`);
  }
  byId("next-failed-gate").addEventListener("click", () => {
    const failures = byId("comparison-gates").querySelectorAll(".failed");
    if (!failures.length) return;
    gateIndex = (gateIndex + 1) % failures.length;
    failures[gateIndex].focus();
    failures[gateIndex].scrollIntoView({ block: "nearest" });
  });
  byId("export-comparison").addEventListener("click", () => {
    if (!current) return;
    const blob = new Blob([JSON.stringify({ schema_version: 1, source, comparison: current }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob), link = document.createElement("a");
    link.href = url; link.download = "simweave-comparison.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
})();
