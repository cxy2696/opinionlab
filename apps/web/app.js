const $ = (id) => document.getElementById(id);
const T = (key) => (window.I18N ? I18N.t(key) : key);
const P = (zh, en) => (window.I18N ? I18N.pick(zh, en) : zh);
const state = {
  templates: [],
  last: null,
  previous: null,
  data: null,
  timer: null,
  index: 0,
};

const COLORS = ["#22d3ee", "#ffb020", "#34d399", "#a78bfa", "#fb7185", "#2dd4bf"];
const chartOptions = { renderer: "canvas" };
const charts = {
  diversity: echarts.init($("chartDiversity"), null, chartOptions),
  shares: echarts.init($("chartShares"), null, chartOptions),
  cascade: echarts.init($("chartCascade"), null, chartOptions),
};
let tracker = null;
if (window.TrackScene && $("trackScene")) {
  tracker = TrackScene.create($("trackScene"), {
    count: 150,
    onTick: ({ step, divergence, active }) => {
      $("trackStep").textContent = String(step).padStart(3, "0");
      $("trackDiv").textContent = divergence.toFixed(2);
      if (active) $("trackStatus").textContent = P("已锁定", "LOCKED");
    },
  });
  $("trackNodes").textContent = "150";
}
const AXIS = { axisLine: { lineStyle: { color: "#1e4a5f" } }, axisLabel: { color: "#7fa6bd", fontSize: 9, fontFamily: "ui-monospace" } };
const SPLIT = { lineStyle: { color: "rgba(30,74,95,.55)" } };

const METRICS = ["diversity_final", "cascade_p99", "time_to_consensus", "absorbing"];

const METRIC_LABELS = {
  diversity_final: ["多样性", "Diversity"],
  cascade_p99: ["级联 P99", "Cascade P99"],
  time_to_consensus: ["收敛步", "Consensus step"],
  absorbing: ["吸收态比例", "Absorbing rate"],
};

function fmt(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value !== "number") return String(value);
  return Math.abs(value) >= 10 ? value.toFixed(1) : value.toFixed(3);
}

function updateLabels() {
  $("qVal").textContent = Number($("q").value).toFixed(1);
}

function currentTemplate() {
  return state.templates.find((item) => item.key === $("template").value);
}

function showQuestion() {
  const template = currentTemplate();
  if (!template) return;
  $("question").innerHTML = `${P(template.question_zh, template.question_en)}`;
  $("reading").innerHTML =
    `<strong>${T("readPrefix")}</strong> ${P(template.interpretation_zh, template.interpretation_en)}`;
}

async function loadTemplates() {
  const response = await fetch("/api/v1/demo/templates");
  const payload = await response.json();
  state.templates = payload.data;
  refreshOptions();
  const requested = new URLSearchParams(location.search).get("template") || "S2";
  if (state.templates.some((item) => item.key === requested)) {
    $("template").value = requested;
  }
  const template = currentTemplate();
  if (template) {
    $("q").value = readParam("q", template.defaults.q);
    $("mu").value = readParam("mu", template.defaults.latency_mu);
    $("steps").value = Math.min(readParam("steps", template.defaults.n_steps), 200);
    $("repeats").value = Math.min(Math.max(readParam("repeats", template.defaults.repeats), 8), 20);
    $("seed").value = readParam("seed", 42);
  }
  showQuestion();
  updateLabels();
}

function refreshOptions() {
  if (!state.templates.length) return;
  const selected = $("template").value;
  $("template").innerHTML = state.templates
    .map((item) => `<option value="${item.key}">${item.key} · ${P(item.name_zh, item.name_en)}</option>`)
    .join("");
  if (state.templates.some((item) => item.key === selected)) $("template").value = selected;
}

function readParam(name, fallback) {
  const value = Number(new URLSearchParams(location.search).get(name));
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function requestBody() {
  return {
    template_key: $("template").value,
    q: Number($("q").value),
    latency_mu: Number($("mu").value),
    steps: Number($("steps").value),
    repeats: Number($("repeats").value),
    seed: Number($("seed").value),
  };
}

function metricCard(key, label, metric) {
  const value = metric && metric.mean !== null && metric.mean !== undefined ? metric.mean : null;
  const ci = metric && metric.ci95_lo !== null && metric.ci95_lo !== undefined
    ? `95% CI ${fmt(metric.ci95_lo)} – ${fmt(metric.ci95_hi)} · n=${metric.n}`
    : "无副本达到多数 / no replica reached a majority";
  const percent = key === "absorbing" ? "1" : "0";
  return `<div class="metric"><div class="name">${label}</div>
    <div class="val" data-target="${value === null ? "null" : value}" data-percent="${percent}">—</div>
    <div class="ci">${ci}</div></div>`;
}

function animateMetrics() {
  document.querySelectorAll("#metrics .val").forEach((el) => {
    const raw = el.dataset.target;
    const target = Number(raw);
    const percent = el.dataset.percent === "1";
    if (raw === "null" || !Number.isFinite(target)) { el.textContent = "—"; return; }
    const started = performance.now();
    const tick = (now) => {
      const progress = Math.min(1, (now - started) / 650);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = target * eased;
      el.textContent = percent
        ? `${(value * 100).toFixed(0)}%`
        : Math.abs(target) >= 10 ? value.toFixed(1) : value.toFixed(3);
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

function renderMetrics(metrics) {
  $("metrics").innerHTML = METRICS
    .map((key) => metricCard(key, P(...METRIC_LABELS[key]), metrics[key]))
    .join("");
  animateMetrics();
}

function sliceUpto(values, index) {
  return values.slice(0, index + 1);
}

function renderCharts(data, upto) {
  const decision = data.decision || {};
  const timing = decision.timing || {};
  const cascadeMarkers = [
    timing.takeoff_step
      ? { xAxis: timing.takeoff_step, label: { formatter: P("起势", "take-off"), position: "insideEndTop", rotate: 0 } }
      : null,
    timing.peak_step
      ? { xAxis: timing.peak_step, label: { formatter: P("峰值", "peak"), position: "insideEndTop", rotate: 0 } }
      : null,
  ].filter(Boolean);

  const series = data.series;
  const index = upto === undefined ? series.steps.length - 1 : upto;
  const steps = series.steps.slice(0, index + 1);
  const bands = series.bands;
  const width = bands.p90.map((high, i) => high - bands.p10[i]);

  const runGradient = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: "rgba(34,211,238,.28)" },
    { offset: 1, color: "rgba(34,211,238,0)" },
  ]);
  charts.diversity.setOption({
    animationDuration: 700,
    animationEasing: "cubicOut",
    animationDurationUpdate: 120,
    textStyle: { color: "#7fa6bd", fontFamily: "ui-monospace" },
    tooltip: { trigger: "axis", backgroundColor: "#02070b", borderColor: "#1e4a5f",
               textStyle: { color: "#d5edf7" } },
    color: ["transparent", "rgba(34,211,238,.16)", "#ffb020", "#22d3ee"],
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, type: "scroll",
              textStyle: { color: "#9ec3d6", fontSize: 10 },
              data: [P("本次运行", "this run"), P("中位数", "median"), "10–90%"] },
    grid: { left: 44, right: 14, top: 30, bottom: 26 },
    xAxis: { type: "category", data: steps, boundaryGap: false, ...AXIS, splitLine: { show: false } },
    yAxis: {
      type: "value", min: 0, ...AXIS, splitLine: SPLIT,
      max: Math.min(1, Math.max(0.5, Math.ceil(Math.max(...series.diversity) * 10) / 10)),
    },
    series: [
      { name: "区间下界", type: "line", stack: "band", data: sliceUpto(bands.p10, index),
        lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, symbol: "none", silent: true },
      { name: "10–90%", type: "line", stack: "band", data: sliceUpto(width, index),
        lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(43,108,176,.16)" },
        symbol: "none", silent: true },
      { name: P("中位数", "median"), type: "line", data: sliceUpto(bands.p50, index),
        smooth: true, showSymbol: false, lineStyle: { type: "dashed", width: 1.4, color: "#ffb020" } },
      { name: P("本次运行", "this run"), type: "line", data: sliceUpto(series.diversity, index),
        smooth: true, showSymbol: false, lineStyle: { width: 2.4, color: "#22d3ee" },
        areaStyle: { color: runGradient } },
    ],
  });

  const opinionCount = data.opinion_count || 2;
  const shares = Array.from({ length: opinionCount }, (_, opinion) => ({
    name: P(`立场 ${opinion}`, `Opinion ${opinion}`),
    type: "line",
    stack: "shares",
    smooth: true,
    showSymbol: false,
    areaStyle: { opacity: 0.7 },
    lineStyle: { width: 1 },
    color: COLORS[opinion % COLORS.length],
    data: sliceUpto(series.shares.map((row) => row[opinion] || 0), index),
  }));
  charts.shares.setOption({
    animationDuration: 700,
    animationEasing: "cubicOut",
    animationDurationUpdate: 120,
    textStyle: { color: "#7fa6bd", fontFamily: "ui-monospace" },
    tooltip: { trigger: "axis", backgroundColor: "#02070b", borderColor: "#1e4a5f",
               textStyle: { color: "#d5edf7" } },
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8,
              textStyle: { color: "#9ec3d6", fontSize: 10 } },
    grid: { left: 40, right: 12, top: 30, bottom: 26 },
    xAxis: { type: "category", data: steps, boundaryGap: false, ...AXIS, splitLine: { show: false } },
    yAxis: { type: "value", min: 0, max: 1, ...AXIS, splitLine: SPLIT },
    series: shares,
  });

  charts.cascade.setOption({
    animationDuration: 700,
    animationEasing: "cubicOut",
    animationDurationUpdate: 120,
    textStyle: { color: "#7fa6bd", fontFamily: "ui-monospace" },
    tooltip: { backgroundColor: "#02070b", borderColor: "#1e4a5f", textStyle: { color: "#d5edf7" } },
    grid: { left: 44, right: 14, top: 30, bottom: 26 },
    xAxis: { type: "category", data: steps, ...AXIS, splitLine: { show: false } },
    yAxis: { type: "value", ...AXIS, splitLine: SPLIT },
    series: [{
      type: "bar",
      data: sliceUpto(series.cascade, index),
      itemStyle: { color: "#ffb020", opacity: 0.8 },
      markLine: cascadeMarkers.length ? { symbol: "none", data: cascadeMarkers } : undefined,
    }],
  });
}

function renderDecision(decision) {
  const panel = $("decision");
  if (!decision) { panel.hidden = true; return; }
  panel.hidden = false;
  $("decisionText").textContent = P(decision.decision_zh, decision.decision_en);
  const timing = decision.timing || {};
  const labels = [
    ["takeoff_step", P("起势", "take-off")],
    ["peak_step", P("峰值", "peak")],
    ["consensus_step", P("多数", "majority")],
    ["intervention_step", P("干预", "intervention")],
  ];
  $("timing").innerHTML = labels
    .filter(([key]) => timing[key] !== null && timing[key] !== undefined)
    .map(([key, label]) => `<span class="chip-timing">${label} <b>step ${timing[key]}</b></span>`)
    .join("");
  $("window").textContent = P(decision.window_zh, decision.window_en);
  const followups = P(decision.followups_zh, decision.followups_en);
  $("followups").innerHTML = followups.map((item) => `<li>${item}</li>`).join("");
  $("caveat").textContent = P(decision.caveat_zh, decision.caveat_en);
}

function renderViews(data) {
  const summary = data.summary_text;
  $("verdict").textContent = P(summary.verdict_zh, summary.verdict_en);
  $("verdict").className = data.summary.absorbing ? "verdict good" : "verdict";
  $("summary").textContent = P(summary.text_zh, summary.text_en);
  renderMetrics(data.metrics);
  renderDecision(data.decision);
  renderCharts(data);
  $("scrub").disabled = false;
  $("scrub").max = String(data.series.steps.length - 1);
  $("scrub").value = String(data.series.steps.length - 1);
  $("play").disabled = false;
  $("download").disabled = false;
  $("copy").disabled = false;
  $("compare").disabled = !state.previous;
  if (tracker) {
    tracker.setData({
      shares: data.series.shares[data.series.shares.length - 1],
      steps: data.series.steps.length,
      peak: Math.max(...data.series.cascade),
      divergence: data.summary.diversity_final,
    });
    $("trackStatus").textContent = P("已锁定", "LOCKED");
    $("trackNodes").textContent = "150";
  }
}

function render(data) {
  if (state.last) state.previous = state.last;
  state.last = data;
  state.data = data;
  renderViews(data);
  renderDelta();
  updateURL();
}

function renderDelta() {
  if (!state.previous || !state.last) return;
  const key = "diversity_final";
  const before = state.previous.metrics[key];
  const after = state.last.metrics[key];
  if (!before || !after) return;
  const diff = after.mean - before.mean;
  const overlap = !(after.ci95_hi < before.ci95_lo || after.ci95_lo > before.ci95_hi);
  const cls = overlap ? "flat" : diff > 0 ? "up" : "down";
  const verdict = overlap
    ? P("置信区间重叠，暂时不能说明有差异", "CIs overlap, no clear difference")
    : diff > 0 ? P("比上一次更分散", "more diverse than the previous run")
               : P("比上一次更集中", "more concentrated than the previous run");
  $("delta").className = `delta ${cls}`;
  $("delta").textContent = P(
    `与上一次相比，多样性 ${diff >= 0 ? "+" : ""}${diff.toFixed(4)}；${verdict}`,
    `Diversity ${diff >= 0 ? "+" : ""}${diff.toFixed(4)} vs the previous run; ${verdict}.`,
  );
}

function updateURL() {
  const params = new URLSearchParams(requestBody());
  params.set("template", $("template").value);
  history.replaceState(null, "", `${location.pathname}?${params.toString()}`);
}

async function run() {
  $("error").textContent = "";
  $("loading").hidden = false;
  $("run").classList.add("running");
  $("run").disabled = true;
  $("status").textContent = T("running");
  try {
    const response = await fetch("/api/v1/demo/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody()),
    });
    const payload = await response.json();
    if (!response.ok || payload.error) throw new Error(payload.error?.message || "request failed");
    render(payload.data);
    $("status").textContent =
      `q=${payload.data.spec.q} · steps=${payload.data.spec.n_steps} · ` +
      `${payload.data.spec.repeats} replicas · seed=${payload.data.spec.seed}`;
  } catch (error) {
    $("error").textContent = error.message;
    $("status").textContent = "";
  } finally {
    $("run").disabled = false;
    $("run").classList.remove("running");
    $("loading").hidden = true;
  }
}

function stopPlayback() {
  if (state.timer) clearInterval(state.timer);
  state.timer = null;
}

function play() {
  if (!state.data) return;
  stopPlayback();
  state.index = 0;
  state.timer = setInterval(() => {
    if (!state.data || state.index >= state.data.series.steps.length - 1) {
      stopPlayback();
      return;
    }
    state.index += 1;
    $("scrub").value = String(state.index);
    renderCharts(state.data, state.index);
  }, 70);
}

async function download() {
  $("status").textContent = "生成报告中… / building report…";
  const response = await fetch("/api/v1/demo/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody()),
  });
  if (!response.ok) {
    $("error").textContent = "report failed";
    return;
  }
  const blob = await response.blob();
  window.open(URL.createObjectURL(blob), "_blank");
  $("status").textContent = "";
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(location.href);
    $("status").textContent = "参数链接已复制 / link copied";
  } catch {
    $("status").textContent = location.href;
  }
}

const PRESETS = {
  quick: { steps: 60, repeats: 8 },
  robust: { repeats: 20 },
  highq: { q: 2.2 },
  slow: { mu: 8 },
};

function updateRange() {
  const input = $("q");
  const ratio = (Number(input.value) - Number(input.min)) / (Number(input.max) - Number(input.min));
  input.style.setProperty("--p", `${(ratio * 100).toFixed(1)}%`);
}

document.querySelectorAll("[data-preset]").forEach((button) => {
  button.onclick = () => {
    const preset = PRESETS[button.dataset.preset];
    if (!preset) return;
    if (preset.steps) $("steps").value = preset.steps;
    if (preset.repeats) $("repeats").value = Math.min(preset.repeats, 20);
    if (preset.q) { $("q").value = preset.q; updateLabels(); updateRange(); }
    if (preset.mu) $("mu").value = preset.mu;
    run();
  };
});

$("reset").onclick = () => {
  const template = currentTemplate();
  if (template) {
    $("q").value = template.defaults.q;
    $("mu").value = template.defaults.latency_mu;
    $("steps").value = Math.min(template.defaults.n_steps, 200);
    $("repeats").value = Math.min(Math.max(template.defaults.repeats, 8), 20);
    $("seed").value = 42;
    updateLabels();
    updateRange();
    run();
  }
};

document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target.tagName !== "BUTTON") {
    event.preventDefault();
    run();
  }
});

$("q").oninput = () => { updateLabels(); updateRange(); };
$("template").onchange = () => {
  const template = currentTemplate();
  if (template) {
    $("q").value = template.defaults.q;
    $("mu").value = template.defaults.latency_mu;
    $("steps").value = Math.min(template.defaults.n_steps, 200);
    $("repeats").value = Math.min(Math.max(template.defaults.repeats, 8), 20);
  }
  state.previous = null;
  $("compare").disabled = true;
  showQuestion();
  updateLabels();
  updateRange();
};
$("run").onclick = run;
$("play").onclick = play;
$("scrub").oninput = () => {
  stopPlayback();
  if (state.data) renderCharts(state.data, Number($("scrub").value));
};
$("download").onclick = download;
$("copy").onclick = copyLink;
window.addEventListener("resize", () => Object.values(charts).forEach((chart) => chart.resize()));

window.addEventListener("languagechange", () => {
  refreshOptions();
  showQuestion();
  updateLabels();
  if (state.data) renderViews(state.data);
  if (state.last) renderDelta();
  if (state.data) {
    $("status").textContent =
      `q=${state.data.spec.q} · steps=${state.data.spec.n_steps} · ` +
      `${state.data.spec.repeats} replicas · seed=${state.data.spec.seed}`;
  }
});
if ($("langToggle")) $("langToggle").onclick = () => I18N.toggle();

loadTemplates()
  .then(() => {
    updateRange();
    if (new URLSearchParams(location.search).get("run") === "1") run();
  })
  .catch((error) => { $("error").textContent = error.message; });
