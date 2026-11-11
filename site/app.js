const $ = (id) => document.getElementById(id);
const state = { templates: [], last: null, previous: null };
const COLORS = ["#2b6cb0", "#dd6b20", "#38a169", "#805ad5", "#d53f8c"];
const charts = {
  diversity: echarts.init($("chartDiversity")),
  shares: echarts.init($("chartShares")),
  cascade: echarts.init($("chartCascade")),
};

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

function showQuestion() {
  const template = currentTemplate();
  if (!template) return;
  $("question").innerHTML = `${template.question_zh}<small>${template.question_en}</small>`;
  $("reading").innerHTML =
    `<strong>怎么读 / How to read:</strong> ${template.interpretation_zh}<br>${template.interpretation_en}`;
}

function applyTemplate(template) {
  $("q").value = template.defaults.q;
  $("mu").value = template.defaults.latency_mu;
  $("steps").value = template.defaults.steps;
  $("repeats").value = Math.min(Math.max(template.defaults.repeats, 8), 20);
  $("seed").value = template.defaults.seed;
  showQuestion();
  $("qVal").textContent = Number($("q").value).toFixed(1);
  state.previous = null;
  $("compare").disabled = true;
}

async function boot() {
  const response = await fetch("./templates.json");
  state.templates = await response.json();
  $("template").innerHTML = state.templates
    .map((item) => `<option value="${item.key}">${item.key} · ${item.name_zh} / ${item.name_en}</option>`)
    .join("");
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
    $("qVal").textContent = Number($("q").value).toFixed(1);
  }
  if (new URLSearchParams(location.search).get("run") === "1") run();
}

function params() {
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

function metricCard(label, value, ci, suffix) {
  let display = fmt(value);
  if (suffix && typeof value === "number") display = `${(value * 100).toFixed(0)}%`;
  const interval = ci ? `95% CI ${fmt(ci[0])} – ${fmt(ci[1])}` : "";
  return `<div class="metric"><div class="name">${label}</div>
    <div class="val">${display}</div><div class="ci">${interval}</div></div>`;
}

function renderMetrics(data) {
  const m = data.metrics;
  $("metrics").innerHTML = [
    metricCard("多样性 / Diversity", m.diversity.mean, [m.diversity.lo, m.diversity.hi]),
    metricCard("级联峰值 / Peak cascade", m.peakValue, null),
    metricCard("达到多数的步 / Majority step", m.consensus ? m.consensus.mean : null, null),
    metricCard("吸收比例 / Absorbing rate", m.absorbing.rate, null, true),
  ].join("");
}

function renderDecision(decision) {
  const panel = $("decision");
  if (!decision) { panel.hidden = true; return; }
  panel.hidden = false;
  $("decisionText").textContent = `${decision.decisionZh} / ${decision.decisionEn}`;
  const labels = [
    ["takeoff", "起势 / take-off"],
    ["peak", "峰值 / peak"],
    ["consensus", "多数 / majority"],
    ["intervention", "干预 / intervention"],
  ];
  $("timing").innerHTML = labels
    .filter(([key]) => decision.timing[key] !== null && decision.timing[key] !== undefined)
    .map(([key, label]) => `<span class="chip">${label} <b>step ${decision.timing[key]}</b></span>`)
    .join("");
  $("window").innerHTML = `${decision.windowZh}<br><span class="muted">${decision.windowEn}</span>`;
  $("followups").innerHTML = decision.followupsZh
    .map((zh, index) => `<li>${zh}<br><span class="muted">${decision.followupsEn[index] || ""}</span></li>`)
    .join("");
  $("caveat").textContent = `${decision.caveatZh} ${decision.caveatEn}`;
}

function renderCharts(data) {
  const first = data.first;
  const steps = first.diversity.map((_, index) => index);
  const width = data.bands.p90.map((value, index) => value - data.bands.p10[index]);
  charts.diversity.setOption({
    color: ["#e2e8f0", "rgba(43,108,176,.16)", "#718096", "#2b6cb0"],
    tooltip: { trigger: "axis" },
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, type: "scroll",
              data: ["本次 / run", "中位数 / median", "10–90%"] },
    grid: { left: 44, right: 14, top: 30, bottom: 26 },
    xAxis: { type: "category", data: steps, boundaryGap: false },
    yAxis: { type: "value", min: 0, max: 0.5 },
    series: [
      { name: "下界", type: "line", stack: "band", data: data.bands.p10, lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, symbol: "none", silent: true },
      { name: "10–90%", type: "line", stack: "band", data: width, lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(43,108,176,.16)" }, symbol: "none", silent: true },
      { name: "中位数 / median", type: "line", data: data.bands.p50, smooth: true, showSymbol: false, lineStyle: { type: "dashed", width: 1.5 } },
      { name: "本次 / run", type: "line", data: first.diversity, smooth: true, showSymbol: false, lineStyle: { width: 2.5 }, areaStyle: { opacity: 0.05 } },
    ],
  });
  charts.shares.setOption({
    tooltip: { trigger: "axis" },
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8 },
    grid: { left: 40, right: 12, top: 30, bottom: 26 },
    xAxis: { type: "category", data: steps, boundaryGap: false },
    yAxis: { type: "value", min: 0, max: 0.5 },
    series: [0, 1].map((opinion) => ({
      name: `立场 ${opinion} / Opinion ${opinion}`,
      type: "line",
      stack: "shares",
      smooth: true,
      showSymbol: false,
      areaStyle: { opacity: 0.7 },
      color: COLORS[opinion],
      data: first.shares.map((row) => row[opinion]),
    })),
  });
  const peak = data.metrics.peakStep;
  charts.cascade.setOption({
    tooltip: {},
    grid: { left: 44, right: 14, top: 30, bottom: 26 },
    xAxis: { type: "category", data: steps.slice(1) },
    yAxis: { type: "value" },
    series: [{
      type: "bar",
      data: first.cascade,
      itemStyle: { color: "#dd6b20", opacity: 0.75 },
      markLine: { symbol: "none", data: [{ xAxis: peak, label: { formatter: "峰值", position: "insideEndTop", rotate: 0 } }] },
    }],
  });
}

function renderSummary(data) {
  const first = data.first;
  const start = first.diversity[0];
  const end = first.finalDiversity;
  const ttc = first.timeToConsensus;
  const verdict = data.metrics.absorbing.rate >= 0.5
    ? "形成稳定共识 / Stable consensus"
    : ttc >= 0 ? "达到多数，但仍在变化 / Majority reached, still moving" : "尚未收敛 / Not converged";
  $("verdict").textContent = verdict;
  $("verdict").className = data.metrics.absorbing.rate >= 0.5 ? "verdict good" : "verdict";
  const zh = ttc >= 0
    ? `在这组假设下，多样性从 ${start.toFixed(2)} 降到 ${end.toFixed(2)}；约在第 ${ttc} 步达到多数。级联峰值在第 ${data.metrics.peakStep} 步（${(data.metrics.peakValue * 100).toFixed(0)}% 的人同时改变立场）。`
    : `在这组假设下，多样性从 ${start.toFixed(2)} 变到 ${end.toFixed(2)}，但在 ${first.diversity.length - 1} 步内没有达到多数。级联峰值在第 ${data.metrics.peakStep} 步。`;
  const en = ttc >= 0
    ? `Under these assumptions diversity fell from ${start.toFixed(2)} to ${end.toFixed(2)}, reaching a majority around step ${ttc}. The cascade peaked at step ${data.metrics.peakStep}.`
    : `Diversity moved from ${start.toFixed(2)} to ${end.toFixed(2)} without a majority in ${first.diversity.length - 1} steps. The cascade peaked at step ${data.metrics.peakStep}.`;
  $("summary").innerHTML = `${zh}<br><span class="muted">${en}</span>`;
}

function renderDelta() {
  if (!state.previous || !state.last) return;
  const before = state.previous.metrics.diversity;
  const after = state.last.metrics.diversity;
  const diff = after.mean - before.mean;
  const overlap = !(after.hi < before.lo || after.lo > before.hi);
  $("delta").className = `delta ${overlap ? "flat" : diff > 0 ? "up" : "down"}`;
  $("delta").textContent = `与上一次相比，多样性 ${diff >= 0 ? "+" : ""}${diff.toFixed(4)}；${overlap ? "置信区间重叠，差异不显著" : diff > 0 ? "更分散" : "更集中"}`;
}

function run() {
  $("error").textContent = "";
  $("status").textContent = "运行中… / running…";
  $("run").disabled = true;
  try {
    const config = params();
    const result = OpinionSim.runMany(config, config.repeats);
    if (state.last) state.previous = state.last;
    state.last = result;
    renderSummary(result);
    renderMetrics(result);
    renderDecision(OpinionSim.decisionBrief(config, result));
    renderCharts(result);
    renderDelta();
    $("csv").disabled = false;
    $("copy").disabled = false;
    $("compare").disabled = !state.previous;
    $("status").textContent = `q=${config.q} · steps=${config.steps} · ${config.repeats} replicas · seed=${config.seed}`;
    const query = new URLSearchParams({
      template: $("template").value,
      q: config.q, mu: config.latency_mu, steps: config.steps,
      repeats: config.repeats, seed: config.seed,
    });
    history.replaceState(null, "", `${location.pathname}?${query.toString()}`);
  } catch (error) {
    $("error").textContent = error.message;
    $("status").textContent = "";
  } finally {
    $("run").disabled = false;
  }
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

$("q").oninput = () => { $("qVal").textContent = Number($("q").value).toFixed(1); };
$("template").onchange = () => { const template = currentTemplate(); if (template) applyTemplate(template); };
$("run").onclick = run;
$("compare").onclick = renderDelta;
$("csv").onclick = downloadCsv;
$("copy").onclick = copyLink;
window.addEventListener("resize", () => Object.values(charts).forEach((chart) => chart.resize()));

boot().catch((error) => { $("error").textContent = error.message; });
