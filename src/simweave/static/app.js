"use strict";
const $ = (id) => document.getElementById(id);
const example = {
  schema_version: 1,
  name: "Cart disturbance recovery",
  adapter: "reference",
  seed: 42,
  world: { timestep: 0.01, steps: 600 },
  robot: {
    kind: "cart_1d",
    mass: 1,
    damping: 0.2,
    initial_position: 0,
    initial_velocity: 0,
  },
  controller: { kind: "pd", target: 1, kp: 8, kd: 4, max_force: 20 },
  sensors: { position_noise_std: 0.005 },
  disturbances: [{ start_step: 200, duration_steps: 30, force: 3 }],
  gates: [{ metric: "final_error", op: "lte", threshold: 0.05 }],
};
let token = "",
  selected = null,
  samples = [],
  runs = [],
  nextBefore = null;
let pollTimer = null,
  animation = null,
  playStart = 0,
  playOffset = 0,
  selectionEpoch = 0;
let submission = null,
  submitting = false,
  currentScale = null;
const active = (run) => run && ["queued", "running"].includes(run.status);
const number = (value) =>
  Number(value).toLocaleString(undefined, { maximumFractionDigits: 4 });
function notice(text, error = false) {
  $("notice").hidden = !text;
  $("notice").textContent = text;
  $("notice").classList.toggle("error", error);
}
async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(path, {
      ...options,
      signal: controller.signal,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const detail = Array.isArray(data.detail)
        ? data.detail.map((e) => `${e.loc.join(".")}: ${e.msg}`).join("; ")
        : data.detail;
      throw new Error(detail || `Request failed (${response.status})`);
    }
    return response;
  } finally {
    clearTimeout(timer);
  }
}
function loadScenario(scenario) {
  $("scenario-json").value = JSON.stringify(scenario, null, 2);
  $("scenario-name").value = scenario.name || "Untitled experiment";
  $("adapter").value = scenario.adapter || "reference";
  $("seed").value = scenario.seed ?? 42;
  $("steps").value = scenario.world?.steps ?? 600;
  $("target").value = scenario.controller?.target ?? 1;
  submission = null;
}
$("reset-example").addEventListener("click", () => {
  loadScenario(structuredClone(example));
  notice("");
});
$("scenario-form").addEventListener("input", (event) => {
  if (event.target.id === "scenario-json") {
    submission = null;
    return;
  }
  try {
    const s = JSON.parse($("scenario-json").value);
    const name = event.target.name;
    if (name === "name") s.name = event.target.value;
    if (name === "adapter") s.adapter = event.target.value;
    if (name === "seed") s.seed = Number(event.target.value);
    if (name === "steps")
      s.world = { ...s.world, steps: Number(event.target.value) };
    if (name === "target")
      s.controller = { ...s.controller, target: Number(event.target.value) };
    $("scenario-json").value = JSON.stringify(s, null, 2);
    submission = null;
  } catch {
    notice("Fix the JSON contract before changing the form fields.", true);
  }
});
$("scenario-json").addEventListener("change", () => {
  try {
    loadScenario(JSON.parse($("scenario-json").value));
  } catch {
    notice("The scenario must be valid JSON.", true);
  }
});
$("connection-toggle").addEventListener("click", () => {
  const open = $("connection-panel").hidden;
  $("connection-panel").hidden = !open;
  $("connection-toggle").setAttribute("aria-expanded", String(open));
});
async function connect(value) {
  stopPlayback();
  clearTimeout(pollTimer);
  selectionEpoch++;
  token = value.trim();
  selected = null;
  samples = [];
  runs = [];
  nextBefore = null;
  document.dispatchEvent(new Event("workspace-reset"));
  renderHistory();
  renderSelected();
  try {
    const capabilities = await (await api("/api/v1/capabilities")).json();
    const mj = capabilities.adapters.find((a) => a.id === "mujoco").available;
    $("adapter").options[1].disabled = !mj;
    $("adapter").options[1].textContent = mj
      ? "MuJoCo"
      : "MuJoCo · unavailable";
    $("mujoco-status").textContent = mj ? "Installed" : "Not installed";
    $("mujoco-dot").classList.toggle("muted", !mj);
    const gz = capabilities.adapters.find((a) => a.id === "gazebo")?.available ?? false;
    $("adapter").querySelector('[value="gazebo"]').disabled = !gz;
    $("adapter").querySelector('[value="gazebo"]').textContent = gz
      ? "Gazebo (ROS 2 cart)" : "Gazebo · unavailable";
    $("gazebo-status").textContent = gz ? "Installed" : "Not installed";
    $("gazebo-dot").classList.toggle("muted", !gz);
    $("connection-state").textContent = "Workspace connected";
    $("connection-dot").classList.remove("muted");
    $("token").value = "";
    $("connection-panel").hidden = true;
    $("connection-toggle").setAttribute("aria-expanded", "false");
    $("launch").disabled = false;
    $("refresh").disabled = false;
    document.dispatchEvent(new Event("workspace-connected"));
    $("run-hint").textContent =
      "Seeded execution · Recorded telemetry · Explicit gates";
    notice("");
    await refresh();
    schedulePoll();
  } catch (error) {
    token = "";
    $("launch").disabled = true;
    $("refresh").disabled = true;
    $("connection-state").textContent = "Not connected";
    $("connection-dot").classList.add("muted");
    $("connection-panel").hidden = false;
    $("connection-toggle").setAttribute("aria-expanded", "true");
    notice(error.message, true);
  }
}
$("connect-form").addEventListener("submit", (e) => {
  e.preventDefault();
  connect($("token").value);
});
$("scenario-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (submitting || !token) return;
  submitting = true;
  $("launch").disabled = true;
  try {
    const body = JSON.stringify(JSON.parse($("scenario-json").value));
    if (!submission || submission.body !== body)
      submission = { body, key: crypto.randomUUID() };
    const run = await (
      await api("/api/v1/runs", {
        method: "POST",
        body,
        headers: { "Idempotency-Key": submission.key },
      })
    ).json();
    submission = null;
    notice("Run queued. The worker will execute your scenario.");
    await refresh();
    await selectRun(run.id);
  } catch (error) {
    notice(error.message, true);
  } finally {
    submitting = false;
    $("launch").disabled = !token;
  }
});
function statusText(run) {
  return run.status === "succeeded" ? "COMPLETED" : run.status.toUpperCase();
}
function statusClass(run) {
  return active(run)
    ? "pending"
    : run.status === "succeeded"
      ? "good"
      : run.status === "failed"
        ? "bad"
        : "neutral";
}
async function refresh(older = false) {
  const sessionToken = token;
  const query =
    older && nextBefore ? `&before=${encodeURIComponent(nextBefore)}` : "";
  const page = await (await api(`/api/v1/runs?limit=20${query}`)).json();
  if (sessionToken !== token) return;
  runs = older ? [...runs, ...page.items] : page.items;
  nextBefore = page.next_before;
  renderHistory();
  document.dispatchEvent(new CustomEvent("runs-changed", { detail: runs }));
}
function renderHistory() {
  $("history").replaceChildren();
  $("history-empty").hidden = runs.length > 0;
  $("history-count").textContent = runs.length;
  $("more").hidden = !nextBefore;
  for (const run of runs) {
    const tr = document.createElement("tr");
    const cells = [
      run.scenario.name,
      run.scenario.adapter,
      String(run.scenario.seed),
      statusText(run),
      run.result ? (run.result.passed ? "PASS" : "FAIL") : "—",
      new Date(run.created_at * 1000).toLocaleString(),
    ];
    cells.forEach((text, index) => {
      const td = document.createElement("td");
      td.textContent = text;
      if (index === 0) {
        const id = document.createElement("small");
        id.textContent = run.id.slice(0, 12);
        td.append(id);
      }
      if (index === 3) {
        const span = document.createElement("span");
        span.textContent = text;
        span.className = `status ${statusClass(run)}`;
        td.replaceChildren(span);
      }
      tr.append(td);
    });
    const td = document.createElement("td"),
      button = document.createElement("button");
    button.className = "text-button";
    button.textContent = "Inspect ↗";
    button.setAttribute(
      "aria-label",
      `Inspect ${run.scenario.name} ${run.id.slice(0, 8)}`,
    );
    button.addEventListener("click", () =>
      selectRun(run.id).catch((error) => notice(error.message, true)),
    );
    td.append(button);
    tr.append(td);
    $("history").append(tr);
  }
}
async function selectRun(id) {
  const epoch = ++selectionEpoch;
  stopPlayback();
  const run = await (await api(`/api/v1/runs/${id}`)).json();
  if (epoch !== selectionEpoch) return;
  selected = run;
  samples = [];
  renderSelected();
  await fetchSamples(epoch);
  if (epoch === selectionEpoch) draw();
}
async function fetchSamples(epoch) {
  let after = samples.length ? samples[samples.length - 1].step : -1;
  while (selected) {
    const page = await (
      await api(
        `/api/v1/runs/${selected.id}/telemetry?after=${after}&limit=1000`,
      )
    ).json();
    if (epoch !== selectionEpoch) return;
    samples.push(...page.items);
    if (page.next_after === null) break;
    after = page.next_after;
  }
}
function renderSelected() {
  const done = selected?.status === "succeeded",
    result = selected?.result;
  $("run-status").textContent = selected
    ? statusText(selected)
    : "NO RUN SELECTED";
  $("run-status").className =
    `status ${selected ? statusClass(selected) : "neutral"}`;
  $("selected-name").textContent =
    selected?.scenario.name || "Your next experiment starts here";
  $("selected-meta").textContent = selected
    ? `${selected.scenario.adapter.toUpperCase()} / SEED ${selected.scenario.seed} / ${selected.id.slice(0, 12)}`
    : "Launch a scenario or select a previous run.";
  $("metric-error").textContent = result
    ? number(result.metrics.final_error)
    : "—";
  $("metric-rmse").textContent = result ? number(result.metrics.rmse) : "—";
  $("metric-gates").textContent = result
    ? `${result.gates.filter((g) => g.passed).length}/${result.gates.length}`
    : "—";
  $("gates-caption").textContent = result
    ? result.passed
      ? "all gates passed"
      : "gates need attention"
    : "awaiting evidence";
  $("gate-details").replaceChildren();
  if (result)
    for (const gate of result.gates) {
      const line = document.createElement("div");
      line.className = gate.passed ? "" : "failed";
      line.textContent = `${gate.passed ? "✓" : "×"} ${gate.metric} ${gate.op === "lte" ? "≤" : "≥"} ${number(gate.threshold)} · observed ${number(gate.value)}`;
      $("gate-details").append(line);
    }
  $("verify").disabled = !done;
  $("download").disabled = !done;
  $("rerun").disabled = !selected;
  $("cancel").hidden = !active(selected);
  $("verification-note").textContent = selected?.error
    ? `Execution failed: ${selected.error}. Load the scenario to try a new run.`
    : selected?.status === "queued"
      ? "Waiting for a worker. Start simweave worker in the server environment."
      : "Replay checks recorded telemetry. Repeatability is scoped to the same engine and environment.";
  draw();
}
function chartScale() {
  let min = Math.min(0, selected?.scenario.controller.target ?? 1),
    max = Math.max(1, selected?.scenario.controller.target ?? 1);
  for (const sample of samples) {
    min = Math.min(min, sample.position);
    max = Math.max(max, sample.position);
  }
  const padding = Math.max((max - min) * 0.12, 0.1);
  min -= padding;
  max += padding;
  return {
    x: (step) =>
      44 + (step / Math.max(1, selected?.scenario.world.steps || 1)) * 656,
    y: (value) => 236 - ((value - min) / (max - min)) * 206,
    min,
    max,
  };
}
function draw() {
  const scale = chartScale();
  currentScale = scale;
  $("chart-grid").replaceChildren();
  for (let i = 0; i < 5; i++) {
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", 44);
    line.setAttribute("x2", 700);
    line.setAttribute("y1", 30 + i * 51.5);
    line.setAttribute("y2", 30 + i * 51.5);
    $("chart-grid").append(line);
    const label = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "text",
    );
    label.setAttribute("x", 3);
    label.setAttribute("y", 33 + i * 51.5);
    label.textContent = (scale.max - ((scale.max - scale.min) * i) / 4).toFixed(
      2,
    );
    $("chart-grid").append(label);
  }
  // Downsample only the drawn polyline. Full-resolution samples remain available for playback/export.
  const stride = Math.max(1, Math.ceil(samples.length / 1000));
  const drawn = samples.filter(
    (s, i) => i % stride === 0 || i === samples.length - 1,
  );
  $("trajectory").setAttribute(
    "points",
    drawn.map((s) => `${scale.x(s.step)},${scale.y(s.position)}`).join(" "),
  );
  const targetY = scale.y(selected?.scenario.controller.target ?? 1);
  $("target-line").setAttribute("y1", targetY);
  $("target-line").setAttribute("y2", targetY);
  $("plot-empty").hidden = samples.length > 0;
  $("sample-count").textContent = `${samples.length.toLocaleString()} samples`;
  $("scrubber").max = Math.max(0, samples.length - 1);
  $("scrubber").disabled = !samples.length;
  $("play").disabled = samples.length < 2;
  const duration = selected
    ? selected.scenario.world.steps * selected.scenario.world.timestep
    : 0;
  $("chart-axis").textContent =
    `SIMULATION TIME / S     0 → ${duration.toFixed(2)}`;
  updatePlayhead();
}
function updatePlayhead() {
  const index = Math.min(Number($("scrubber").value), samples.length - 1),
    sample = samples[index];
  if (!sample) {
    $("replay-time").textContent = "0.00 s";
    return;
  }
  const scale = currentScale || chartScale(),
    x = scale.x(sample.step);
  $("playhead").setAttribute("x1", x);
  $("playhead").setAttribute("x2", x);
  $("play-dot").setAttribute("cx", x);
  $("play-dot").setAttribute("cy", scale.y(sample.position));
  $("replay-time").textContent = `${sample.time.toFixed(2)} s`;
  $("chart").setAttribute(
    "aria-label",
    `Step ${sample.step}: position ${number(sample.position)} metres at ${sample.time.toFixed(2)} seconds`,
  );
}
function stopPlayback() {
  if (animation) cancelAnimationFrame(animation);
  animation = null;
  $("play").textContent = "▶";
  $("play").setAttribute("aria-label", "Play telemetry");
}
$("play").addEventListener("click", () => {
  if (animation) {
    stopPlayback();
    return;
  }
  if (!selected || samples.length < 2) return;
  if (Number($("scrubber").value) >= samples.length - 1)
    $("scrubber").value = 0;
  playOffset = Number($("scrubber").value);
  playStart = performance.now();
  const speed = Number($("speed").value);
  $("play").textContent = "Ⅱ";
  $("play").setAttribute("aria-label", "Pause telemetry");
  function tick(now) {
    const next =
      playOffset +
      Math.floor(
        (((now - playStart) / 1000) * speed) / selected.scenario.world.timestep,
      );
    $("scrubber").value = Math.min(next, samples.length - 1);
    updatePlayhead();
    if (next >= samples.length - 1) stopPlayback();
    else animation = requestAnimationFrame(tick);
  }
  animation = requestAnimationFrame(tick);
});
$("scrubber").addEventListener("input", () => {
  stopPlayback();
  updatePlayhead();
});
$("speed").addEventListener("change", stopPlayback);
$("verify").addEventListener("click", async () => {
  try {
    const result = await (
      await api(`/api/v1/runs/${selected.id}/verify`, { method: "POST" })
    ).json();
    notice(
      `Recording verified. Quality gates ${result.passed ? "passed" : "failed"}.`,
    );
  } catch (error) {
    notice(error.message, true);
  }
});
$("download").addEventListener("click", async () => {
  try {
    const id = selected.id,
      response = await api(`/api/v1/runs/${id}/recording`),
      url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `${id}.jsonl`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    notice(error.message, true);
  }
});
$("rerun").addEventListener("click", () => {
  loadScenario(selected.scenario);
  $("scenario-name").focus();
  notice(
    "Scenario loaded. Run it to create a new experiment with the same seed.",
  );
});
$("cancel").addEventListener("click", async () => {
  try {
    await api(`/api/v1/runs/${selected.id}/cancel`, { method: "POST" });
    await selectRun(selected.id);
    await refresh();
  } catch (error) {
    notice(error.message, true);
  }
});
$("refresh").addEventListener("click", () =>
  refresh().catch((error) => notice(error.message, true)),
);
$("more").addEventListener("click", () =>
  refresh(true).catch((error) => notice(error.message, true)),
);
function schedulePoll() {
  clearTimeout(pollTimer);
  pollTimer = setTimeout(async () => {
    if (!token) return;
    try {
      if (active(selected)) {
        const epoch = selectionEpoch,
          id = selected.id;
        const latest = await (await api(`/api/v1/runs/${id}`)).json();
        if (epoch === selectionEpoch) {
          selected = latest;
          await fetchSamples(epoch);
          if (epoch === selectionEpoch) renderSelected();
        }
      }
      if (runs.some(active)) await refresh();
    } catch (error) {
      notice(error.message, true);
    }
    schedulePoll();
  }, 1500);
}
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    clearTimeout(pollTimer);
    stopPlayback();
  } else if (token) schedulePoll();
});
loadScenario(structuredClone(example));
draw();
const initialToken = new URLSearchParams(location.hash.slice(1)).get("token");
if (initialToken) {
  history.replaceState(null, "", location.pathname);
  connect(initialToken);
}
