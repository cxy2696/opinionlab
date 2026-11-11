const $ = (id) => document.getElementById(id);
const state = {
  templates: [],
  last: null,
  previous: null,
  data: null,
  timer: null,
  index: 0,
};

const COLORS = ["#2b6cb0", "#dd6b20", "#38a169", "#805ad5", "#d53f8c", "#319795"];
const chartOptions = { renderer: "canvas" };
const charts = {
  diversity: echarts.init($("chartDiversity"), null, chartOptions),
  shares: echarts.init($("chartShares"), null, chartOptions),
  cascade: echarts.init($("chartCascade"), null, chartOptions),
};

const METRICS = [
  ["diversity_final", "多样性 / Diversity"],
  ["cascade_p99", "级联 P99 / Cascade P99"],
  ["time_to_consensus", "收敛步 / Consensus step"],
  ["absorbing", "吸收态比例 / Absorbing rate"],
];

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
  $("question").innerHTML = `${template.question_zh}<small>${template.question_en}</small>`;
  $("reading").innerHTML =
    `<strong>怎么读 / How to read:</strong> ${template.interpretation_zh}<br>${template.interpretation_en}`;
}

async function loadTemplates() {
  const response = await fetch("/api/v1/demo/templates");
  const payload = await response.json();
  state.templates = payload.data;
  $("template").innerHTML = state.templates
    .map((item) => `<option value="${item.key}">${item.key} · ${item.name_zh} / ${item.name_en}</option>`)
    .join("");
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
  const value = metric ? metric.mean : null;
  let display = fmt(value);
  if (key === "absorbing" && typeof value === "number") display = `${(value * 100).toFixed(0)}%`;
  const ci = metric && metric.ci95_lo !== null && metric.ci95_lo !== undefined
    ? `95% CI ${fmt(metric.ci95_lo)} – ${fmt(metric.ci95_hi)} · n=${metric.n}`
    : "无副本达到多数 / no replica reached a majority";
  return `<div class="metric"><div class="name">${label}</div>
    <div class="val">${display}</div><div class="ci">${ci}</div></div>`;
}

function renderMetrics(metrics) {
  $("metrics").innerHTML = METRICS
    .map(([key, label]) => metricCard(key, label, metrics[key]))
    .join("");
}

function sliceUpto(values, index) {
  return values.slice(0, index + 1);
}

function renderCharts(data, upto) {
  const series = data.series;
  const index = upto === undefined ? series.steps.length - 1 : upto;
  const steps = series.steps.slice(0, index + 1);
  const bands = series.bands;
  const width = bands.p90.map((high, i) => high - bands.p10[i]);

  charts.diversity.setOption({
    animationDurationUpdate: 60,
    tooltip: { trigger: "axis" },
    color: ["#e2e8f0", "rgba(43,108,176,.16)", "#718096", "#2b6cb0"],
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, type: "scroll",
              data: ["本次 / run", "中位数 / median", "10–90%"] },
    grid: { left: 44, right: 14, top: 30, bottom: 26 },
    xAxis: { type: "category", data: steps, boundaryGap: false },
    yAxis: {
      type: "value", min: 0,
      max: Math.min(1, Math.max(0.5, Math.ceil(Math.max(...series.diversity) * 10) / 10)),
    },
    series: [
      { name: "区间下界", type: "line", stack: "band", data: sliceUpto(bands.p10, index),
        lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, symbol: "none", silent: true },
      { name: "10–90%", type: "line", stack: "band", data: sliceUpto(width, index),
        lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(43,108,176,.16)" },
        symbol: "none", silent: true },
      { name: "中位数 / median", type: "line", data: sliceUpto(bands.p50, index),
        smooth: true, showSymbol: false, lineStyle: { type: "dashed", width: 1.5 } },
      { name: "本次 / run", type: "line", data: sliceUpto(series.diversity, index),
        smooth: true, showSymbol: false, lineStyle: { width: 2.5 },
        areaStyle: { opacity: 0.05 } },
    ],
  });

  const opinionCount = data.opinion_count || 2;
  const shares = Array.from({ length: opinionCount }, (_, opinion) => ({
    name: `立场 ${opinion} / Opinion ${opinion}`,
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
    animationDurationUpdate: 60,
    tooltip: { trigger: "axis" },
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8 },
    grid: { left: 40, right: 12, top: 30, bottom: 26 },
    xAxis: { type: "category", data: steps, boundaryGap: false },
    yAxis: { type: "value", min: 0, max: 1 },
    series: shares,
  });

  charts.cascade.setOption({
    animationDurationUpdate: 60,
    tooltip: {},
    grid: { left: 44, right: 14, top: 18, bottom: 26 },
    xAxis: { type: "category", data: steps },
    yAxis: { type: "value" },
    series: [{
      type: "bar",
      data: sliceUpto(series.cascade, index),
      itemStyle: { color: "#dd6b20", opacity: 0.75 },
    }],
  });
}

function render(data) {
  if (state.last) state.previous = state.last;
  state.last = data;
  state.data = data;
  const summary = data.summary_text;
  $("verdict").textContent = `${summary.verdict_zh} / ${summary.verdict_en}`;
  $("verdict").className = data.summary.absorbing ? "verdict good" : "verdict";
  $("summary").innerHTML = `${summary.text_zh}<br><span class="muted">${summary.text_en}</span>`;
  renderMetrics(data.metrics);
  renderCharts(data);
  $("scrub").disabled = false;
  $("scrub").max = String(data.series.steps.length - 1);
  $("scrub").value = String(data.series.steps.length - 1);
  $("play").disabled = false;
  $("download").disabled = false;
  $("copy").disabled = false;
  $("compare").disabled = !state.previous;
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
    ? "置信区间重叠，暂时不能说明有差异 / CIs overlap, no clear difference"
    : diff > 0 ? "比上一次更分散 / more diverse than the previous run"
               : "比上一次更集中 / more concentrated than the previous run";
  $("delta").className = `delta ${cls}`;
  $("delta").textContent = `与上一次相比，多样性 ${diff >= 0 ? "+" : ""}${diff.toFixed(4)}；${verdict}`;
}

function updateURL() {
  const params = new URLSearchParams(requestBody());
  params.set("template", $("template").value);
  history.replaceState(null, "", `${location.pathname}?${params.toString()}`);
}

async function run() {
  $("error").textContent = "";
  $("status").textContent = "运行中… / running…";
  $("run").disabled = true;
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

$("q").oninput = updateLabels;
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

loadTemplates()
  .then(() => {
    if (new URLSearchParams(location.search).get("run") === "1") run();
  })
  .catch((error) => { $("error").textContent = error.message; });
