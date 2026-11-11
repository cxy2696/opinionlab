const $ = (id) => document.getElementById(id);
const T = (key) => (window.I18N ? I18N.t(key) : key);
const P = (zh, en) => (window.I18N ? I18N.pick(zh, en) : zh);
const state = { templates: [], last: null, previous: null, config: null, timer: null, index: 0 };
const COLORS = ["#22d3ee", "#ffb020", "#34d399", "#a78bfa", "#fb7185"];
const charts = {
  diversity: echarts.init($("chartDiversity")),
  shares: echarts.init($("chartShares")),
  cascade: echarts.init($("chartCascade")),
};
const particleFields = [];
function addParticles(id, chart, mode) {
  if (window.TrackParticles && $(id)) particleFields.push(TrackParticles.create($(id), chart, mode));
}
addParticles("particlesDiversity", charts.diversity, "line");
addParticles("particlesShares", charts.shares, "shares");
addParticles("particlesCascade", charts.cascade, "cascade");

function tickClock() {
  if (!$("cockpitClock")) return;
  const now = new Date();
  $("cockpitClock").textContent =
    [now.getUTCHours(), now.getUTCMinutes(), now.getUTCSeconds()]
      .map((value) => String(value).padStart(2, "0")).join(":");
}
tickClock();
setInterval(tickClock, 1000);

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

function fmt(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value !== "number") return String(value);
  return Math.abs(value) >= 10 ? value.toFixed(1) : value.toFixed(3);
}

function readParam(name, fallback) {
  const value = Number(new URLSearchParams(location.search).get(name));
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function currentTemplate() {
  return state.templates.find((item) => item.key === $("template").value);
}

function updateLabels() {
  $("qVal").textContent = Number($("q").value).toFixed(1);
}

function updateRange() {
  const input = $("q");
  const ratio = (Number(input.value) - Number(input.min)) / (Number(input.max) - Number(input.min));
  input.style.setProperty("--p", `${(ratio * 100).toFixed(1)}%`);
}

function showQuestion() {
  const template = currentTemplate();
  if (!template) return;
  $("question").innerHTML = P(template.question_zh, template.question_en);
  $("reading").innerHTML =
    `<strong>${T("readPrefix")}</strong> ${P(template.interpretation_zh, template.interpretation_en)}`;
}

function applyTemplate(template) {
  $("q").value = template.defaults.q;
  $("mu").value = template.defaults.latency_mu;
  $("steps").value = template.defaults.steps;
  $("repeats").value = Math.min(Math.max(template.defaults.repeats, 8), 20);
  $("seed").value = template.defaults.seed;
  state.previous = null;
  $("compare").disabled = true;
  showQuestion();
  updateLabels();
  updateRange();
}

async function boot() {
  const response = await fetch("./templates.json");
  state.templates = await response.json();
  refreshOptions();
  const requested = new URLSearchParams(location.search).get("template") || "S2";
  if (state.templates.some((item) => item.key === requested)) $("template").value = requested;
  const template = currentTemplate();
  if (template) {
    applyTemplate(template);
    $("q").value = readParam("q", template.defaults.q);
    $("mu").value = readParam("mu", template.defaults.latency_mu);
    $("steps").value = readParam("steps", template.defaults.steps);
    $("repeats").value = Math.min(Math.max(readParam("repeats", template.defaults.repeats), 8), 20);
    $("seed").value = readParam("seed", template.defaults.seed);
    updateLabels();
    updateRange();
  }
  if (new URLSearchParams(location.search).get("run") === "1") run();
}

function refreshOptions() {
  if (!state.templates.length) return;
  const selected = $("template").value;
  $("template").innerHTML = state.templates
    .map((item) => `<option value="${item.key}">${item.key} · ${P(item.name_zh, item.name_en)}</option>`)
    .join("");
  if (state.templates.some((item) => item.key === selected)) $("template").value = selected;
}

function config() {
  const template = currentTemplate();
  return Object.assign({}, template.defaults, {
    q: Number($("q").value),
    latency_mu: Number($("mu").value),
    steps: Number($("steps").value),
    repeats: Number($("repeats").value),
    seed: Number($("seed").value),
    intervention: template.intervention,
  });
}

const METRIC_WHY = {
  diversity: ["越低越集中；0 表示只剩一种立场。", "Lower is more concentrated; 0 means one stance left."],
  peak: ["级联最剧烈的一步，多少人同时改变立场。", "The most intense step: how many changed at once."],
  consensus: ["达到 80% 多数所需的步数；只统计达到多数的副本。", "Steps to an 80% majority; majority-reaching replicas only."],
  absorbing: ["有多少副本最终稳定在多数。", "Share of replicas that end in a stable majority."],
};

function metricCard(label, value, ci, percent, why) {
  const target = value === null || value === undefined ? "null" : value;
  const interval = ci ? `95% CI ${fmt(ci[0])} – ${fmt(ci[1])}` : "";
  return `<div class="metric"><div class="name">${label}</div>
    <div class="val" data-target="${target}" data-percent="${percent ? "1" : "0"}">—</div>
    <div class="ci">${interval}</div><div class="why">${why || ""}</div></div>`;
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
      el.textContent = percent ? `${(value * 100).toFixed(0)}%`
        : Math.abs(target) >= 10 ? value.toFixed(1) : value.toFixed(3);
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

function renderMetrics(data) {
  const m = data.metrics;
  $("metrics").innerHTML = [
    metricCard(P("多样性", "Diversity"), m.diversity.mean, [m.diversity.lo, m.diversity.hi], false, P(...METRIC_WHY.diversity)),
    metricCard(P("级联峰值", "Peak cascade"), m.peakValue, null, false, P(...METRIC_WHY.peak)),
    metricCard(P("达到多数的步", "Majority step"), m.consensus ? m.consensus.mean : null, null, false, P(...METRIC_WHY.consensus)),
    metricCard(P("吸收比例", "Absorbing rate"), m.absorbing.rate, null, true, P(...METRIC_WHY.absorbing)),
  ].join("");
  animateMetrics();
}

function renderPlain(data) {
  const m = data.metrics;
  const diversity = m.diversity.mean;
  const absorbing = m.absorbing.rate;
  const consensus = m.consensus ? m.consensus.mean : null;
  const cascade = data.first.cascade;
  const peak = cascade.length ? Math.max(...cascade) : 0;
  const peakStep = cascade.length ? cascade.indexOf(peak) + 1 : 0;
  const bullets = [];
  bullets.push(P(
    `最终多样性 ${fmt(diversity)}：${diversity < 0.05 ? "基本只剩一种声音" : diversity < 0.2 ? "仍有少数派，但明显收拢" : "多种立场仍然并存"}。`,
    `Final diversity ${fmt(diversity)}: ${diversity < 0.05 ? "one stance dominates" : diversity < 0.2 ? "minority remains but shrinking" : "multiple stances still coexist"}.`,
  ));
  if (cascade.length) {
    bullets.push(P(
      `级联峰值在第 ${peakStep} 步，约 ${(peak * 100).toFixed(0)}% 的人同时改变立场。`,
      `The cascade peaked at step ${peakStep}; about ${(peak * 100).toFixed(0)}% changed at once.`,
    ));
  }
  if (consensus !== null) {
    bullets.push(P(`约第 ${consensus.toFixed(1)} 步达到 80% 多数。`, `An 80% majority is reached around step ${consensus.toFixed(1)}.`));
  }
  bullets.push(P(
    `${(absorbing * 100).toFixed(0)}% 的副本最终稳定在多数。`,
    `${(absorbing * 100).toFixed(0)}% of replicas end in a stable majority.`,
  ));
  $("plainReading").innerHTML =
    `<strong>${P("用一句话说：", "In plain words:")}</strong><ul>${bullets.map((item) => `<li>${item}</li>`).join("")}</ul>`;
}

function renderDecision(decision) {
  const panel = $("decision");
  if (!decision) { panel.hidden = true; return; }
  panel.hidden = false;
  $("decisionText").textContent = P(decision.decisionZh, decision.decisionEn);
  const labels = [
    ["takeoff", P("起势", "take-off")],
    ["peak", P("峰值", "peak")],
    ["consensus", P("多数", "majority")],
    ["intervention", P("干预", "intervention")],
  ];
  $("timing").innerHTML = labels
    .filter(([key]) => decision.timing[key] !== null && decision.timing[key] !== undefined)
    .map(([key, label]) => `<span class="chip-timing">${label} <b>step ${decision.timing[key]}</b></span>`)
    .join("");
  $("window").textContent = P(decision.windowZh, decision.windowEn);
  $("followups").innerHTML = P(decision.followupsZh, decision.followupsEn).map((item) => `<li>${item}</li>`).join("");
  $("caveat").textContent = P(decision.caveatZh, decision.caveatEn);
}

function slice(values, index) { return values.slice(0, index + 1); }

function renderCharts(data, upto) {
  const first = data.first;
  const index = upto === undefined ? first.diversity.length - 1 : upto;
  const steps = first.diversity.slice(0, index + 1).map((_, i) => i);
  const width = data.bands.p90.map((value, i) => value - data.bands.p10[i]);
  const gradient = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: "rgba(34,211,238,.28)" },
    { offset: 1, color: "rgba(34,211,238,0)" },
  ]);
  charts.diversity.setOption({
    animationDuration: 700, animationEasing: "cubicOut", animationDurationUpdate: 120,
    textStyle: { color: "#7fa6bd", fontFamily: "ui-monospace" },
    tooltip: { trigger: "axis", backgroundColor: "#02070b", borderColor: "#1e4a5f",
               textStyle: { color: "#d5edf7" } },
    color: ["transparent", "rgba(34,211,238,.16)", "#ffb020", "#22d3ee"],
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, type: "scroll",
              textStyle: { color: "#9ec3d6", fontSize: 10 },
              data: [P("本次运行", "this run"), P("中位数", "median"), "10–90%"] },
    grid: { left: 44, right: 14, top: 30, bottom: 26 },
    xAxis: { type: "category", data: steps, boundaryGap: false, ...AXIS, splitLine: { show: false } },
    yAxis: { type: "value", min: 0, max: 0.5, ...AXIS, splitLine: SPLIT },
    series: [
      { name: "下界", type: "line", stack: "band", data: slice(data.bands.p10, index),
        lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, symbol: "none", silent: true },
      { name: "10–90%", type: "line", stack: "band", data: slice(width, index),
        lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(34,211,238,.16)" }, symbol: "none", silent: true },
      { name: P("中位数", "median"), type: "line", data: slice(data.bands.p50, index),
        smooth: true, showSymbol: false, lineStyle: { type: "dashed", width: 1.4, color: "#ffb020" } },
      { name: P("本次运行", "this run"), type: "line", data: slice(first.diversity, index),
        smooth: true, showSymbol: false, lineStyle: { width: 2.4, color: "#22d3ee" },
        areaStyle: { color: gradient } },
    ],
  });

  charts.shares.setOption({
    animationDuration: 700, animationEasing: "cubicOut", animationDurationUpdate: 120,
    textStyle: { color: "#7fa6bd", fontFamily: "ui-monospace" },
    tooltip: { trigger: "axis", backgroundColor: "#02070b", borderColor: "#1e4a5f",
               textStyle: { color: "#d5edf7" } },
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8,
              textStyle: { color: "#9ec3d6", fontSize: 10 } },
    grid: { left: 40, right: 12, top: 30, bottom: 26 },
    xAxis: { type: "category", data: steps, boundaryGap: false, ...AXIS, splitLine: { show: false } },
    yAxis: { type: "value", min: 0, max: 1, ...AXIS, splitLine: SPLIT },
    series: [0, 1].map((opinion) => ({
      name: P(`立场 ${opinion}`, `Opinion ${opinion}`),
      type: "line", stack: "shares", smooth: true, showSymbol: false,
      areaStyle: { opacity: 0.65 }, lineStyle: { width: 1 },
      color: COLORS[opinion], data: slice(first.shares.map((row) => row[opinion]), index),
    })),
  });

  const peak = data.metrics.peakStep;
  charts.cascade.setOption({
    animationDuration: 700, animationEasing: "cubicOut", animationDurationUpdate: 120,
    textStyle: { color: "#7fa6bd", fontFamily: "ui-monospace" },
    tooltip: { backgroundColor: "#02070b", borderColor: "#1e4a5f", textStyle: { color: "#d5edf7" } },
    grid: { left: 44, right: 14, top: 30, bottom: 26 },
    xAxis: { type: "category", data: steps.slice(1), ...AXIS, splitLine: { show: false } },
    yAxis: { type: "value", ...AXIS, splitLine: SPLIT },
    series: [{
      type: "bar", data: slice(first.cascade, Math.max(0, index - 1)),
      itemStyle: { color: "#ffb020", opacity: 0.8 },
      markLine: { symbol: "none", data: [{ xAxis: peak, label: { formatter: P("峰值", "peak"), position: "insideEndTop", rotate: 0 } }] },
    }],
  });

  if (particleFields.length === 3) {
    particleFields[0].setData(first.diversity.slice(0, index + 1));
    particleFields[1].setData(first.shares.slice(0, index + 1));
    particleFields[2].setData(first.cascade.slice(0, index + 1));
  }
}

function renderSummary(data) {
  const first = data.first;
  const start = first.diversity[0];
  const end = first.finalDiversity;
  const ttc = first.timeToConsensus;
  const stable = data.metrics.absorbing.rate >= 0.5;
  const verdict = stable ? P("形成稳定共识", "Stable consensus")
    : ttc >= 0 ? P("达到多数，但仍在变化", "Majority reached, still moving")
               : P("尚未收敛", "Not converged");
  $("verdict").textContent = verdict;
  $("verdict").className = stable ? "verdict good" : "verdict";
  const zh = ttc >= 0
    ? `在这组假设下，多样性从 ${start.toFixed(2)} 降到 ${end.toFixed(2)}；约在第 ${ttc} 步达到多数。级联峰值在第 ${data.metrics.peakStep} 步（${(data.metrics.peakValue * 100).toFixed(0)}% 的人同时改变立场）。`
    : `在这组假设下，多样性从 ${start.toFixed(2)} 变到 ${end.toFixed(2)}，但在 ${first.diversity.length - 1} 步内没有达到多数。级联峰值在第 ${data.metrics.peakStep} 步。`;
  const en = ttc >= 0
    ? `Under these assumptions diversity fell from ${start.toFixed(2)} to ${end.toFixed(2)}, reaching a majority around step ${ttc}. The cascade peaked at step ${data.metrics.peakStep}.`
    : `Diversity moved from ${start.toFixed(2)} to ${end.toFixed(2)} without a majority in ${first.diversity.length - 1} steps. The cascade peaked at step ${data.metrics.peakStep}.`;
  $("summary").textContent = P(zh, en);
}

function renderDelta() {
  if (!state.previous || !state.last) return;
  const before = state.previous.metrics.diversity;
  const after = state.last.metrics.diversity;
  const diff = after.mean - before.mean;
  const overlap = !(after.hi < before.lo || after.lo > before.hi);
  $("delta").className = `delta ${overlap ? "flat" : diff > 0 ? "up" : "down"}`;
  $("delta").textContent = P(
    `与上一次相比，多样性 ${diff >= 0 ? "+" : ""}${diff.toFixed(4)}；${overlap ? "置信区间重叠，差异不显著" : diff > 0 ? "更分散" : "更集中"}`,
    `Diversity ${diff >= 0 ? "+" : ""}${diff.toFixed(4)} vs the previous run; ${overlap ? "CIs overlap, no clear difference" : diff > 0 ? "more diverse" : "more concentrated"}.`,
  );
}

function run() {
  $("error").textContent = "";
  $("loading").hidden = false;
  $("run").classList.add("running");
  $("run").disabled = true;
  $("status").textContent = T("running");
  try {
    const settings = config();
    const result = OpinionSim.runMany(settings, settings.repeats);
    if (state.last) state.previous = state.last;
    state.last = result;
    state.config = settings;
    renderSummary(result);
    renderMetrics(result);
    renderPlain(result);
    renderDecision(OpinionSim.decisionBrief(settings, result, $("template").value));
    renderCharts(result);
    renderDelta();
    if (tracker) {
      tracker.setData({
        shares: result.first.shares[result.first.shares.length - 1],
        steps: result.first.diversity.length,
        peak: result.metrics.peakValue,
        divergence: result.first.finalDiversity,
      });
      $("trackStatus").textContent = P("已锁定", "LOCKED");
      $("trackNodes").textContent = "150";
    }
    $("csv").disabled = false;
    $("copy").disabled = false;
    $("compare").disabled = !state.previous;
    $("scrub").disabled = false;
    $("play").disabled = false;
    $("scrub").max = String(result.first.diversity.length - 1);
    $("scrub").value = String(result.first.diversity.length - 1);
    $("status").textContent = `q=${settings.q} · steps=${settings.steps} · ${settings.repeats} replicas · seed=${settings.seed}`;
    const query = new URLSearchParams({ template: $("template").value, q: settings.q,
      mu: settings.latency_mu, steps: settings.steps, repeats: settings.repeats, seed: settings.seed });
    history.replaceState(null, "", `${location.pathname}?${query.toString()}`);
  } catch (error) {
    $("error").textContent = error.message;
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
  if (!state.last) return;
  stopPlayback();
  state.index = 0;
  state.timer = setInterval(() => {
    if (!state.last || state.index >= state.last.first.diversity.length - 1) { stopPlayback(); return; }
    state.index += 1;
    $("scrub").value = String(state.index);
    renderCharts(state.last, state.index);
  }, 70);
}

function downloadCsv() {
  if (!state.last) return;
  const first = state.last.first;
  const rows = [["step", "diversity", "cascade", "share0", "share1"]];
  for (let i = 0; i < first.diversity.length; i += 1) {
    rows.push([i, first.diversity[i], i ? first.cascade[i - 1] : 0, first.shares[i][0], first.shares[i][1]]);
  }
  const blob = new Blob([rows.map((row) => row.join(",")).join("\n")], { type: "text/csv" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "opinionlab-demo.csv";
  link.click();
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
    applyTemplate(template);
    run();
  }
};

document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target.tagName !== "BUTTON") { event.preventDefault(); run(); }
});

$("q").oninput = () => { updateLabels(); updateRange(); };
$("template").onchange = () => { const template = currentTemplate(); if (template) applyTemplate(template); };
$("run").onclick = run;
$("play").onclick = play;
$("scrub").oninput = () => { stopPlayback(); if (state.last) renderCharts(state.last, Number($("scrub").value)); };
$("csv").onclick = downloadCsv;
$("copy").onclick = copyLink;
$("compare").onclick = renderDelta;
window.addEventListener("resize", () => Object.values(charts).forEach((chart) => chart.resize()));

window.addEventListener("languagechange", () => {
  refreshOptions();
  showQuestion();
  updateLabels();
  if (state.last) {
    renderSummary(state.last);
    renderMetrics(state.last);
    renderPlain(state.last);
    renderDecision(OpinionSim.decisionBrief(state.config, state.last, $("template").value));
    renderCharts(state.last);
    renderDelta();
  }
});
if ($("langToggle")) $("langToggle").onclick = () => I18N.toggle();

boot().catch((error) => { $("error").textContent = error.message; });
