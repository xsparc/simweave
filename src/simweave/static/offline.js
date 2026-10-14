"use strict";
(() => {
  const data = JSON.parse(document.getElementById("report-data").textContent);
  const report = data.review, byId = (id) => document.getElementById(id);
  const number = (v) => v !== 0 && Math.abs(v) < .0001 ? v.toExponential(3) : Number(v).toLocaleString(undefined, {maximumSignificantDigits: 7});
  const failed = (p) => Boolean(p.error || !p.comparison.passed);
  let gateIndex = -1, exportURL = null;
  byId("title").textContent = report.name;
  byId("outcome").textContent = ["PASS", "GATES FAIL", "ERROR"][report.exit_code];
  byId("outcome").className = report.exit_code ? "fail" : "pass";
  byId("count").textContent = report.pairs.length;
  byId("failures").textContent = `${report.pairs.filter(p => !p.error && failed(p)).length} / ${report.pairs.filter(p => p.error).length}`;
  byId("digest").textContent = `SUITE SHA256 / ${report.suite_digest}`;
  for (const [i, p] of report.pairs.entries()) byId("pair").add(new Option(`${p.name} · ${p.adapter} · seed ${p.seed} · ${p.error ? "ERROR" : failed(p) ? "FAIL" : "PASS"}`, String(i)));
  byId("pair").value = String(Math.max(0, report.pairs.findIndex(failed)));
  byId("next").disabled = !report.pairs.some(failed);
  const env = data.environment;
  const fields = env ? {"Source revision": env.source_revision || "Unknown (not supplied)", "Image ID": env.image_id || "Unknown (container rerun unavailable)", "Python / system / architecture": `${env.python} / ${env.system} / ${env.architecture}`, "Implementation SHA256": env.implementation_digest, ...env.dependencies} : {Provenance: "Unknown: report converted without its original runtime metadata"};
  for (const [key, value] of Object.entries(fields)) {
    const dt = document.createElement("dt"), dd = document.createElement("dd");
    dt.textContent = key; dd.textContent = value || "Not installed"; byId("environment").append(dt, dd);
  }
  function selected() { return report.pairs[Number(byId("pair").value)]; }
  function render() {
    const p = selected(), c = p.comparison;
    gateIndex = -1;
    byId("export-panel").hidden = true;
    if (exportURL) { URL.revokeObjectURL(exportURL); exportURL = null; }
    byId("export-text").value = ""; byId("download").removeAttribute("href");
    byId("pair-title").textContent = `${p.name} / seed ${p.seed}`;
    byId("selection").textContent = `${p.adapter} · ${p.baseline_id} → ${p.candidate_id}`;
    byId("status").textContent = p.error ? "EXECUTION ERROR" : c.passed ? "GATES PASS" : "GATES FAIL";
    byId("status").className = `badge ${failed(p) ? "fail" : "pass"}`;
    byId("error").hidden = !p.error; byId("comparison").hidden = Boolean(p.error);
    byId("error").textContent = p.error ? `${p.error}. No complete comparison is available. The export preserves suite inputs for diagnosis.` : "";
    byId("setup").textContent = ["baseline", "candidate"].map(role => {const s = data.suite[role]; return `${role}: kp ${number(s.kp)} · kd ${number(s.kd)} · force limit ${number(s.max_force)} N`;}).join(" / ");
    byId("warning").textContent = c ? c.warnings.join(" ") : "Execution errors are distinct from quality gate failures.";
    byId("metrics").replaceChildren(); byId("gates").replaceChildren();
    if (!c) return;
    for (const m of c.metrics) {
      const row = document.createElement("tr");
      for (const text of [m.metric, number(m.baseline), number(m.candidate), `${m.delta > 0 ? "+" : ""}${number(m.delta)}`]) {const cell = document.createElement("td"); cell.textContent = text; row.append(cell);}
      byId("metrics").append(row);
    }
    const gate = (text, pass) => {const el = document.createElement("p"); el.textContent = text; el.className = `gate ${pass ? "" : "failed"}`; el.tabIndex = -1; byId("gates").append(el);};
    for (const role of ["baseline", "candidate"]) c[role].result.gates.forEach((g, i) => gate(`${role} · ${g.passed ? "PASS" : role === "candidate" && c.newly_failing_gates.includes(i) ? "NEW FAILURE" : "FAIL"} · ${g.metric} ${g.op === "lte" ? "≤" : "≥"} ${number(g.threshold)} · observed ${number(g.value)}`, g.passed));
    c.regression_gates.forEach(g => gate(`regression · ${g.passed ? "PASS" : "FAIL"} · ${g.metric} increase ≤ ${number(g.max_increase)} · observed ${number(g.increase)}`, g.passed));
    byId("next-gate").disabled = !byId("gates").querySelector(".failed");
    const points = [...c.baseline.trajectory, ...c.candidate.trajectory], target = c.baseline.scenario.controller.target;
    const low = Math.min(0, target, ...points.map(p => p.position)), high = Math.max(1, target, ...points.map(p => p.position));
    const pad = Math.max((high-low)*.1, .1), min = low-pad, max = high+pad;
    const duration = c.baseline.scenario.world.steps*c.baseline.scenario.world.timestep;
    const x = t => 48+t/duration*654, y = v => 210-(v-min)/(max-min)*195;
    for (const role of ["baseline", "candidate"]) byId(role).setAttribute("points", c[role].trajectory.map(p => `${x(p.time)},${y(p.position)}`).join(" "));
    byId("target").setAttribute("y1", y(target)); byId("target").setAttribute("y2", y(target));
    byId("ticks").replaceChildren();
    for (let i=0; i<5; i++) {const v = min+(max-min)*i/4, t = document.createElementNS("http://www.w3.org/2000/svg", "text"); t.setAttribute("x", "0"); t.setAttribute("y", y(v)+3); t.textContent = number(v); byId("ticks").append(t);}
    byId("axis-label").textContent = `POSITION / M · SIMULATION TIME / S · 0 → ${number(duration)}`;
    byId("chart").setAttribute("aria-label", `Baseline and candidate position in metres over ${number(duration)} seconds. Numeric changes follow in the metric table.`);
  }
  byId("pair").addEventListener("change", render);
  byId("next").addEventListener("click", () => {
    const start = Number(byId("pair").value);
    for (let n=1; n<=report.pairs.length; n++) {const i = (start+n)%report.pairs.length; if (failed(report.pairs[i])) {byId("pair").value = String(i); render(); break;}}
  });
  byId("next-gate").addEventListener("click", () => {const gates = byId("gates").querySelectorAll(".failed"); if (gates.length) gates[(++gateIndex)%gates.length].focus();});
  byId("export").addEventListener("click", () => {
    const payload = {schema_version: 1, suite_digest: report.suite_digest, suite: data.suite, environment: env, pair: selected()};
    const text = JSON.stringify(payload, null, 2);
    if (exportURL) URL.revokeObjectURL(exportURL);
    exportURL = URL.createObjectURL(new Blob([text], {type: "application/json"}));
    byId("download").href = exportURL;
    byId("export-text").value = text;
    byId("export-panel").hidden = false;
    byId("export-status").textContent = `Export ready: ${selected().candidate_id} · seed ${selected().seed}. Save the JSON file or copy its contents below.`;
    byId("download").focus();
  });
  render();
})();
