/*
 * OpinionLab web client.
 *
 * One source serves both product surfaces:
 *   - `mode=api`    : the local FastAPI service, which runs the real Python engine.
 *   - `mode=static` : the GitHub Pages build, which runs the lightweight binary
 *                     simulator in `sim.js` and reads `templates.json`.
 *
 * Both backends are normalised to the same payload before rendering, so the
 * layout, charts, decision brief and exports cannot drift apart again.
 */
const $ = (id) => document.getElementById(id);
const T = (key) => (window.I18N ? I18N.t(key) : key);
const P = (zh, en, ja, de) => (window.I18N ? I18N.pick(zh, en, ja, de) : zh);
const MODE = (document.querySelector('meta[name="opinionlab-mode"]')?.content || "api").toLowerCase();
const IS_STATIC = MODE === "static";
const API_BASE = "/api/v1/demo";

const state = {
  templates: [],
  features: {},
  limits: {},
  last: null,
  previous: null,
  data: null,
  timer: null,
  index: 0,
  preview: false,
  showPrevious: true,
};

const COLORS = ["#22d3ee", "#ffb020", "#34d399", "#a78bfa", "#fb7185", "#2dd4bf"];
const chartOptions = { renderer: "canvas" };
const charts = {};
if (window.echarts) {
  charts.diversity = echarts.init($("chartDiversity"), null, chartOptions);
  charts.shares = echarts.init($("chartShares"), null, chartOptions);
  charts.cascade = echarts.init($("chartCascade"), null, chartOptions);
}

function eachChart(callback) {
  Object.values(charts).forEach((chart) => chart && callback(chart));
}

if (window.TrackGalaxy && $("galaxyScene")) TrackGalaxy.create($("galaxyScene"));

const fields = [];
if (window.TrackField) {
  [["fieldWave", "wave"], ["fieldBars", "bars"], ["fieldCloud", "cloud"]].forEach(([id, mode]) => {
    if ($(id)) fields.push(TrackField.create($(id), mode));
  });
}

const particleFields = [];
function addParticles(id, chart, mode) {
  if (window.TrackParticles && $(id) && chart) {
    particleFields.push(TrackParticles.create($(id), chart, mode));
  }
}
addParticles("particlesDiversity", charts.diversity, "line");
addParticles("particlesShares", charts.shares, "shares");
addParticles("particlesCascade", charts.cascade, "cascade");

const clamp = (value, low, high) => Math.min(high, Math.max(low, value));

function tickClock() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  const time = [now.getHours(), now.getMinutes(), now.getSeconds()].map(pad).join(":");
  if ($("cockpitClock")) {
    $("cockpitClock").textContent =
      [now.getUTCHours(), now.getUTCMinutes(), now.getUTCSeconds()].map(pad).join(":");
  }
  if ($("heroClock")) $("heroClock").textContent = time;
  if ($("heroDate")) {
    const locale = window.I18N ? I18N.locale : "en-GB";
    $("heroDate").textContent = new Intl.DateTimeFormat(locale, {
      year: "numeric", month: "2-digit", day: "2-digit",
    }).format(now);
  }
}
tickClock();
setInterval(tickClock, 1000);

let tracker = null;
if (window.TrackScene && $("trackScene")) {
  tracker = TrackScene.create($("trackScene"), {
    count: 150,
    onTick: ({ step, divergence, active }) => {
      if ($("trackStep")) $("trackStep").textContent = String(step).padStart(3, "0");
      if ($("trackDiv")) $("trackDiv").textContent = divergence.toFixed(2);
      if (active && $("trackStatus")) $("trackStatus").textContent = T("trackLocked");
    },
  });
  if ($("trackNodes")) $("trackNodes").textContent = "150";
}

const AXIS = { axisLine: { lineStyle: { color: "#1e4a5f" } }, axisLabel: { color: "#7fa6bd", fontSize: 9, fontFamily: "ui-monospace" } };
const SPLIT = { lineStyle: { color: "rgba(30,74,95,.55)" } };

const METRICS = [
  "diversity_final",
  "cascade_p99",
  "time_to_consensus",
  "absorbing",
  "entropy_final",
  "polarization_final",
];

const METRIC_LABELS = {
  diversity_final: ["多样性", "Diversity", "多様性", "Diversität"],
  cascade_p99: ["级联 P99", "Cascade P99", "カスケード P99", "Kaskade P99"],
  time_to_consensus: ["多数到达步", "Majority step", "多数到達ステップ", "Mehrheitsschritt"],
  absorbing: ["稳定多数比例", "Stable majority", "安定多数の割合", "Stabile Mehrheit"],
  entropy_final: ["观点熵", "Entropy", "意見エントロピー", "Entropie"],
  polarization_final: ["极化度", "Polarization", "分極度", "Polarisierung"],
};

const METRIC_WHY = {
  diversity_final: [
    "越低越集中；0 表示只剩一种立场。",
    "Lower is more concentrated; 0 means one stance left.",
    "低いほど集中しており、0 は一つの立場だけが残った状態です。",
    "Niedriger bedeutet konzentrierter; 0 heißt, dass nur eine Haltung übrig bleibt.",
  ],
  cascade_p99: [
    "最剧烈的 1% 步数里，改变立场的人占比；反映级联尾部风险。",
    "Share changing in the most intense 1% of steps; a tail-risk read on cascades.",
    "最も激しい1%のステップで立場を変えた人の割合。カスケードの裾リスクを示します。",
    "Anteil der Wechsel in den intensivsten 1 % der Schritte; ein Tail-Risiko-Maß für Kaskaden.",
  ],
  time_to_consensus: [
    "达到 80% 多数所需的步数；只统计达到多数的副本。",
    "Steps to an 80% majority; majority-reaching replicas only.",
    "80%の多数に達するまでのステップ数。多数に達した複製のみを集計します。",
    "Schritte bis zu einer 80 %-Mehrheit; nur Replikate, die eine Mehrheit erreichen.",
  ],
  absorbing: [
    "有多少副本最终稳定在多数；低于 50% 说明结果仍在变化。",
    "Share of replicas that end in a stable majority; below 50% means the group is still moving.",
    "最終的に安定した多数に至った複製の割合。50%未満ならまだ変化中です。",
    "Anteil der Replikate, die in einer stabilen Mehrheit enden; unter 50 % bewegt sich die Gruppe noch.",
  ],
  entropy_final: [
    "以比特计的观点分散度；比多样性更敏感于少数派。",
    "Opinion spread in bits; more sensitive to a surviving minority than diversity.",
    "ビット単位の意見の広がり。多様性より少数派に敏感です。",
    "Meinungsstreuung in Bit; empfindlicher für eine verbleibende Minderheit als Diversität.",
  ],
  polarization_final: [
    "归一化后的阵营分裂度；0 = 一致，1 = 均匀多阵营。",
    "Normalised camp split; 0 = unanimity, 1 = an even multi-camp split.",
    "正規化した陣営の分裂度。0 = 一致、1 = 均等な多陣営。",
    "Normierte Lagerteilung; 0 = Einigkeit, 1 = gleichmäßige Mehrlagerteilung.",
  ],
};

function fmt(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value !== "number") return String(value);
  return Math.abs(value) >= 10 ? value.toFixed(1) : value.toFixed(3);
}

function text(id, value) {
  const node = $(id);
  if (node) node.textContent = value === null || value === undefined ? "" : String(value);
}

function updateLabels() {
  const value = Number($("q").value).toFixed(1);
  text("qVal", value);
  text("qScaleValue", value);
}

function updateRange() {
  const input = $("q");
  if (!input) return;
  const ratio = (Number(input.value) - Number(input.min)) / (Number(input.max) - Number(input.min));
  input.style.setProperty("--p", `${(ratio * 100).toFixed(1)}%`);
}

function currentTemplate() {
  return state.templates.find((item) => item.key === $("template").value);
}

function normalizeTemplate(template) {
  const defaults = Object.assign({}, template.defaults || {});
  defaults.q = Number(defaults.q ?? 1.5);
  defaults.latency_mu = Number(defaults.latency_mu ?? 3);
  defaults.latency_sigma = Number(defaults.latency_sigma ?? 1);
  defaults.latency_dist = defaults.latency_dist || "normal";
  defaults.steps = Number(defaults.steps ?? defaults.n_steps ?? 100);
  defaults.repeats = Math.max(8, Number(defaults.repeats ?? 8));
  defaults.seed = Number(defaults.seed ?? 42);
  defaults.n_nodes = Number(defaults.n_nodes ?? 300);
  defaults.n_edges = Number(defaults.n_edges ?? 800);
  defaults.min_size = Number(defaults.min_size ?? 2);
  defaults.max_size = Number(defaults.max_size ?? 5);
  defaults.init_mode = defaults.init_mode || (template.init_mode ?? "balanced_random");
  defaults.target_share_1 = Number(defaults.target_share_1 ?? 0.5);
  return Object.assign({}, template, { defaults });
}

function fillBrief(id, value, asList) {
  const node = $(id);
  if (!node) return;
  node.textContent = "";
  const parts = asList
    ? value.split(/(?:；|;)\s*/u).map((part) => part.trim()).filter(Boolean)
    : [value];
  if (parts.length > 1) {
    const list = document.createElement("ul");
    parts.forEach((part) => {
      const item = document.createElement("li");
      item.textContent = part;
      list.appendChild(item);
    });
    node.appendChild(list);
  } else {
    node.textContent = value;
  }
}

function renderScenarioBrief(template) {
  if (!template) return;
  const real = I18N.template(template, "real_world") || I18N.template(template, "interpretation");
  const params = I18N.template(template, "parameters") || T("briefParametersFallback");
  const watch = I18N.template(template, "watch") || T("briefWatchFallback");
  fillBrief("briefRealWorld", real, false);
  fillBrief("briefParameters", params, true);
  fillBrief("briefWatch", watch, true);
  fillBrief("briefAssumptions", I18N.template(template, "assumptions"), false);
  fillBrief("briefLimitations", I18N.template(template, "limitations"), false);
}

function showQuestion() {
  const template = currentTemplate();
  if (!template) return;
  if ($("question")) $("question").innerHTML = I18N.template(template, "question");
  if ($("reading")) {
    $("reading").innerHTML =
      `<strong>${T("readPrefix")}</strong> ${I18N.template(template, "interpretation")}`;
  }
  renderScenarioBrief(template);
  updateHeroTemplate(template);
}

function updateHeroTemplate(template) {
  if (!template) return;
  if ($("heroScenario")) {
    $("heroScenario").textContent = `${template.key} · ${I18N.template(template, "name")}`;
  }
  if (!state.data && $("heroRunMeta")) {
    $("heroRunMeta").textContent = P(
      `预览 // ${template.key} 默认参数`,
      `PREVIEW // ${template.key} DEFAULT`,
      `プレビュー // ${template.key} デフォルト`,
      `VORSCHAU // ${template.key} STANDARD`,
    );
  }
}

function setGauge(wrapId, valueId, value) {
  const wrap = $(wrapId);
  const output = $(valueId);
  if (!wrap || !output) return;
  const clamped = clamp(Number(value) || 0, 0, 100);
  wrap.style.setProperty("--gauge", clamped.toFixed(1));
  output.textContent = String(Math.round(clamped));
}

function updateInstrumentFromData(data) {
  if (!$("heroReplicas") || !data) return;
  const metrics = data.metrics || {};
  const diversityMetric = metrics.diversity_final || {};
  const diversity = diversityMetric.mean;
  const cohesion = diversity === null || diversity === undefined ? 0 : (1 - clamp(diversity, 0, 1)) * 100;
  const cascade = (data.series && data.series.cascade) || [];
  const peak = cascade.length ? Math.max(...cascade) * 100 : 0;
  let peakStep = null;
  if (data.decision && data.decision.timing) peakStep = data.decision.timing.peak_step;
  if (peakStep === null && cascade.length) peakStep = cascade.indexOf(Math.max(...cascade)) + 1;
  const consensus = metrics.time_to_consensus ? metrics.time_to_consensus.mean : null;
  const n = diversityMetric.n || (data.spec && data.spec.repeats) || 0;
  const halfCi = diversityMetric.ci95_hi !== null && diversityMetric.ci95_hi !== undefined
    ? (diversityMetric.ci95_hi - diversityMetric.ci95_lo) / 2 : null;
  setGauge("gaugeCohesionWrap", "gaugeCohesion", cohesion);
  setGauge("gaugeTurnWrap", "gaugeTurn", peak);
  text("heroReplicas", String(n));
  text("heroMajority", consensus === null || consensus === undefined ? "—" : consensus.toFixed(1));
  text("heroPeakStep", peakStep === null || peakStep === undefined ? "—" : String(peakStep));
  text("heroCi", halfCi === null ? "—" : `±${halfCi.toFixed(3)}`);
  if ($("heroRunMeta")) {
    $("heroRunMeta").textContent = state.preview
      ? P(
          `预览结果 // ${n} 个副本`,
          `PREVIEW // ${n} REPLICAS`,
          `プレビュー // ${n} 複製`,
          `VORSCHAU // ${n} REPLIKATE`,
        )
      : P(
          `运行结果 // ${n} 个副本`,
          `LIVE RUN // ${n} REPLICAS`,
          `実行結果 // ${n} 複製`,
          `LIVE-LAUF // ${n} REPLIKATE`,
        );
  }
}

function syncLimits() {
  const limits = state.limits || {};
  const minSteps = Number(limits.min_steps ?? 10);
  const maxSteps = Number(limits.max_steps ?? 200);
  const minRepeats = Number(limits.min_repeats ?? 1);
  const maxRepeats = Number(limits.max_repeats ?? 20);
  if ($("steps")) {
    $("steps").min = String(minSteps);
    $("steps").max = String(maxSteps);
  }
  if ($("repeats")) {
    $("repeats").min = String(minRepeats);
    $("repeats").max = String(maxRepeats);
  }
  text("limitNote", P(
    `演示上限：${maxSteps} 步 · ${maxRepeats} 副本；完整引擎可跑 30+ 副本。`,
    `Demo caps: ${maxSteps} steps · ${maxRepeats} replicas; the full engine supports 30+ replicas.`,
    `デモ上限：${maxSteps}ステップ・${maxRepeats}複製。完全版は30以上の複製に対応します。`,
    `Demo-Grenzen: ${maxSteps} Schritte · ${maxRepeats} Replikate; die vollständige Engine erlaubt 30+.`,
  ));
}

function readParam(name, fallback) {
  const value = Number(new URLSearchParams(location.search).get(name));
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function readSeed(fallback) {
  const raw = new URLSearchParams(location.search).get("seed");
  if (raw === null || raw.trim() === "") return fallback;
  const value = Number(raw);
  return Number.isFinite(value) && value >= 0 ? value : fallback;
}

function applyTemplate(template, options) {
  if (!template) return;
  const useUrl = Boolean(options && options.useUrl);
  const d = template.defaults;
  const limits = state.limits || {};
  const minSteps = Number(limits.min_steps ?? 10);
  const maxSteps = Number(limits.max_steps ?? 200);
  const minRepeats = Number(limits.min_repeats ?? 1);
  const maxRepeats = Number(limits.max_repeats ?? 20);
  const pick = (name, fallback) => (useUrl ? readParam(name, fallback) : fallback);
  if ($("q")) $("q").value = clamp(pick("q", d.q), 0.5, 3).toFixed(1);
  if ($("mu")) $("mu").value = clamp(pick("mu", d.latency_mu), 1, 60);
  if ($("steps")) $("steps").value = clamp(pick("steps", d.steps), minSteps, maxSteps);
  if ($("repeats")) $("repeats").value = clamp(pick("repeats", d.repeats), minRepeats, maxRepeats);
  if ($("seed")) $("seed").value = useUrl ? readSeed(d.seed) : d.seed;
  state.previous = null;
  state.last = null;
  state.showPrevious = true;
  if ($("compare")) {
    $("compare").disabled = true;
    $("compare").setAttribute("aria-pressed", "false");
    $("compare").classList.remove("active");
  }
  showQuestion();
  updateLabels();
  updateRange();
}

async function loadTemplates() {
  const url = IS_STATIC ? "./templates.json" : `${API_BASE}/templates`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  const payload = await response.json();
  const list = Array.isArray(payload) ? payload : payload.data;
  state.templates = (list || []).map(normalizeTemplate);
  state.features = (payload && payload.features) || { ollama: false };
  state.limits = (payload && payload.limits) || {};
  refreshOptions();
  syncLimits();
  const requested = new URLSearchParams(location.search).get("template") || "S2";
  if (state.templates.some((item) => item.key === requested) && $("template")) {
    $("template").value = requested;
  }
  applyTemplate(currentTemplate(), { useUrl: true });
}

function refreshOptions() {
  if (!state.templates.length || !$("template")) return;
  const selected = $("template").value;
  $("template").innerHTML = state.templates
    .map((item) => `<option value="${item.key}">${item.key} · ${I18N.template(item, "name")}</option>`)
    .join("");
  if (state.templates.some((item) => item.key === selected)) $("template").value = selected;
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

function dataRequestBody() {
  const spec = (state.data && state.data.spec) || {};
  const template = (state.data && state.data.template) || currentTemplate() || {};
  return {
    template_key: template.key || $("template").value,
    q: spec.q ?? Number($("q").value),
    latency_mu: spec.latency_mu ?? Number($("mu").value),
    steps: spec.n_steps ?? spec.steps ?? Number($("steps").value),
    repeats: spec.repeats ?? Number($("repeats").value),
    seed: spec.seed ?? Number($("seed").value),
  };
}

function staticSettings() {
  const template = currentTemplate();
  const d = template.defaults;
  return Object.assign({}, d, {
    q: Number($("q").value),
    latency_mu: Number($("mu").value),
    latency_sigma: d.latency_sigma,
    latency_dist: d.latency_dist,
    steps: Number($("steps").value),
    repeats: Number($("repeats").value),
    seed: Number($("seed").value),
    init_mode: d.init_mode,
    target_share_1: d.target_share_1,
    intervention: template.intervention,
    templateKey: template.key,
    template,
  });
}

function metricCard(key, label, metric) {
  const value = metric && metric.mean !== null && metric.mean !== undefined ? metric.mean : null;
  const hasCi = metric && metric.ci95_lo !== null && metric.ci95_lo !== undefined;
  // Student-t intervals for bounded metrics can extend past the feasible
  // range at small n. Keep the estimate unchanged but clamp the displayed
  // interval so a negative diversity or a >100% share never appears.
  let low = hasCi ? metric.ci95_lo : null;
  let high = hasCi ? metric.ci95_hi : null;
  if (hasCi && key !== "time_to_consensus") low = Math.max(0, low);
  if (hasCi && ["diversity_final", "cascade_p99", "absorbing", "polarization_final"].includes(key)) {
    high = Math.min(1, high);
  }
  const ci = hasCi
    ? `95% CI ${fmt(low)} – ${fmt(high)} · n=${metric.n}`
    : T("noMajority");
  const percent = key === "absorbing" ? "1" : "0";
  return `<div class="metric"><div class="name">${label}</div>
    <div class="val" data-target="${value === null ? "null" : value}" data-percent="${percent}">—</div>
    <div class="ci">${ci}</div><div class="why">${P(...METRIC_WHY[key])}</div></div>`;
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
  if (!$("metrics")) return;
  $("metrics").innerHTML = METRICS
    .map((key) => metricCard(key, P(...METRIC_LABELS[key]), metrics[key]))
    .join("");
  animateMetrics();
}

function renderQuality(data) {
  const node = $("quality");
  if (!node) return;
  const quality = data.quality;
  if (!quality) { node.hidden = true; return; }
  const bits = [];
  bits.push(`<span class="chip-quality">${T("qualityEngine")} <b>${quality.engine}</b></span>`);
  if (quality.graph) {
    bits.push(`<span class="chip-quality">${quality.graph.n_nodes} nodes · ${quality.graph.n_edges} edges</span>`);
  }
  bits.push(`<span class="chip-quality">${quality.replicas} ${T("qualityReplicas")}</span>`);
  if (quality.censored_replicas) {
    bits.push(`<span class="chip-quality warn">${quality.censored_replicas}/${quality.replicas} ${T("qualityCensored")}</span>`);
  }
  if (quality.insufficient_samples) {
    bits.push(`<span class="chip-quality warn">${T("qualityUnderpowered")}</span>`);
  }
  const warnings = Object.values(quality.warnings || {}).reduce((sum, value) => sum + Number(value), 0);
  if (warnings) bits.push(`<span class="chip-quality warn">${warnings} ${T("qualityWarnings")}</span>`);
  if (IS_STATIC) bits.push(`<span class="chip-quality">${T("qualityPreview")}</span>`);
  node.innerHTML = bits.join("");
  node.hidden = false;
}

function sliceUpto(values, index) {
  return values.slice(0, index + 1);
}

function chartFrame(data, index, previous) {
  const series = data.series;
  const bands = series.bands;
  const width = bands.p90.map((high, i) => high - bands.p10[i]);
  const opinionCount = data.opinion_count || 2;
  const diversity = [
    { data: sliceUpto(bands.p10, index) },
    { data: sliceUpto(width, index) },
    { data: sliceUpto(bands.p50, index) },
    { data: sliceUpto(series.diversity, index) },
  ];
  if (previous) {
    diversity.push({ data: previous.series.diversity.slice(0, index + 1) });
  }
  return {
    diversity,
    shares: Array.from({ length: opinionCount }, (_, opinion) => ({
      data: sliceUpto(series.shares.map((row) => row[opinion] || 0), index),
    })),
    cascade: [{ data: sliceUpto(series.cascade, index) }],
  };
}

function renderCharts(data, upto, options) {
  if (!window.echarts || !charts.diversity) return;
  const playback = Boolean(options && options.playback);
  const decision = data.decision || {};
  const timing = decision.timing || {};
  const markers = [
    timing.takeoff_step ? { xAxis: timing.takeoff_step, label: { formatter: P("起势", "take-off", "立ち上がり", "Anlauf"), position: "insideEndTop", rotate: 0 } } : null,
    timing.peak_step ? { xAxis: timing.peak_step, label: { formatter: P("峰值", "peak", "ピーク", "Peak"), position: "insideEndTop", rotate: 0 } } : null,
    timing.consensus_step ? { xAxis: timing.consensus_step, label: { formatter: P("多数", "majority", "多数", "Mehrheit"), position: "insideEndTop", rotate: 0 } } : null,
  ].filter(Boolean);

  const series = data.series;
  const index = upto === undefined ? series.steps.length - 1 : upto;
  const previous = state.previous && state.showPrevious ? state.previous : null;
  const frame = chartFrame(data, index, previous);

  if (playback) {
    // Fast path: keep the axes and legend fixed and only replace the point
    // arrays. No enter/update animation, no layout pass, no markLine rebuild.
    charts.diversity?.setOption({ animation: false, series: frame.diversity },
      { lazyUpdate: true, silent: true });
    charts.shares?.setOption({ animation: false, series: frame.shares },
      { lazyUpdate: true, silent: true });
    charts.cascade?.setOption({ animation: false, series: frame.cascade },
      { lazyUpdate: true, silent: true });
  } else {
    const runGradient = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
      { offset: 0, color: "rgba(34,211,238,.28)" },
      { offset: 1, color: "rgba(34,211,238,0)" },
    ]);
    const diversitySeries = [
      { name: "区间下界", type: "line", stack: "band", data: sliceUpto(series.bands.p10, index),
        lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, symbol: "none", silent: true },
      { name: "10–90%", type: "line", stack: "band", data: sliceUpto(series.bands.p90.map((high, i) => high - series.bands.p10[i]), index),
        lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(43,108,176,.16)" },
        symbol: "none", silent: true },
      { name: P("中位数", "median", "中央値", "Median"), type: "line", data: sliceUpto(series.bands.p50, index),
        smooth: true, showSymbol: false, lineStyle: { type: "dashed", width: 1.4, color: "#ffb020" } },
      { name: P("本次运行", "this run", "今回の実行", "dieser Lauf"), type: "line", data: sliceUpto(series.diversity, index),
        smooth: true, showSymbol: false, lineStyle: { width: 2.4, color: "#22d3ee" },
        areaStyle: { color: runGradient },
        markLine: markers.length ? { symbol: "none", lineStyle: { color: "#3f7288", type: "dotted" }, data: markers } : undefined },
    ];
    if (previous) {
      diversitySeries.push({
        name: T("previousRun"), type: "line", data: previous.series.diversity.slice(0, index + 1),
        smooth: true, showSymbol: false, lineStyle: { width: 1.2, type: "dashed", color: "#94a3b8" },
        itemStyle: { color: "#94a3b8" },
      });
    }
    const legendData = [
      P("本次运行", "this run", "今回の実行", "dieser Lauf"),
      P("中位数", "median", "中央値", "Median"),
      "10–90%",
    ];
    if (previous) legendData.push(T("previousRun"));
    charts.diversity?.setOption({
      animation: true,
      animationDuration: 700, animationEasing: "cubicOut", animationDurationUpdate: 120,
      textStyle: { color: "#7fa6bd", fontFamily: "ui-monospace" },
      tooltip: { trigger: "axis", backgroundColor: "#02070b", borderColor: "#1e4a5f", textStyle: { color: "#d5edf7" } },
      legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, type: "scroll",
                textStyle: { color: "#9ec3d6", fontSize: 10 }, data: legendData },
      grid: { left: 44, right: 14, top: 30, bottom: 26 },
      xAxis: { type: "category", data: series.steps, boundaryGap: false, ...AXIS, splitLine: { show: false } },
      yAxis: { type: "value", min: 0, ...AXIS, splitLine: SPLIT,
               max: Math.min(1, Math.max(0.5, Math.ceil(Math.max(...series.diversity) * 10) / 10)) },
      series: diversitySeries,
    }, { replaceMerge: ["series"] });

    const opinionCount = data.opinion_count || 2;
    const shares = Array.from({ length: opinionCount }, (_, opinion) => ({
      name: P(`立场 ${opinion}`, `Opinion ${opinion}`, `立場 ${opinion}`, `Haltung ${opinion}`),
      type: "line", stack: "shares", smooth: true, showSymbol: false,
      areaStyle: { opacity: 0.7 }, lineStyle: { width: 1 },
      color: COLORS[opinion % COLORS.length],
      data: sliceUpto(series.shares.map((row) => row[opinion] || 0), index),
    }));
    charts.shares?.setOption({
      animation: true,
      animationDuration: 700, animationEasing: "cubicOut", animationDurationUpdate: 120,
      textStyle: { color: "#7fa6bd", fontFamily: "ui-monospace" },
      tooltip: { trigger: "axis", backgroundColor: "#02070b", borderColor: "#1e4a5f", textStyle: { color: "#d5edf7" } },
      legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { color: "#9ec3d6", fontSize: 10 } },
      grid: { left: 40, right: 12, top: 30, bottom: 26 },
      xAxis: { type: "category", data: series.steps, boundaryGap: false, ...AXIS, splitLine: { show: false } },
      yAxis: { type: "value", min: 0, max: 1, ...AXIS, splitLine: SPLIT },
      series: shares,
    }, { replaceMerge: ["series"] });

    charts.cascade?.setOption({
      animation: true,
      animationDuration: 700, animationEasing: "cubicOut", animationDurationUpdate: 120,
      textStyle: { color: "#7fa6bd", fontFamily: "ui-monospace" },
      tooltip: { backgroundColor: "#02070b", borderColor: "#1e4a5f", textStyle: { color: "#d5edf7" } },
      grid: { left: 44, right: 14, top: 30, bottom: 26 },
      xAxis: { type: "category", data: series.steps, ...AXIS, splitLine: { show: false } },
      yAxis: { type: "value", ...AXIS, splitLine: SPLIT },
      series: [{
        type: "bar", data: sliceUpto(series.cascade, index),
        itemStyle: { color: "#ffb020", opacity: 0.8 },
        markLine: markers.length ? { symbol: "none", lineStyle: { color: "#6b7f8c", type: "dotted" }, data: markers } : undefined,
      }],
    }, { replaceMerge: ["series"] });
  }

  // Decorative overlays are throttled during playback: they refresh every two
  // steps instead of fighting the charts for every frame.
  const total = series.steps.length - 1;
  const decorate = !playback || index === 0 || index === total
    || state.decoIndex === undefined || Math.abs(index - state.decoIndex) >= 2;
  if (decorate) {
    state.decoIndex = index;
    if (particleFields.length === 3) {
      particleFields[0].setData(series.diversity.slice(0, index + 1));
      particleFields[1].setData(series.shares.slice(0, index + 1));
      particleFields[2].setData(series.cascade.slice(0, index + 1));
    }
    if (fields.length === 3) {
      const payload = { diversity: series.diversity.slice(0, index + 1),
        cascade: series.cascade.slice(0, index + 1), shares: series.shares.slice(0, index + 1) };
      fields.forEach((field) => field.setData(payload));
      renderFieldStats(payload);
    }
  }
}

function decisionCopy(decision) {
  const timing = decision.timing || {};
  const peak = timing.peak_step;
  const takeoff = timing.takeoff_step;
  const consensus = timing.consensus_step;
  const intervention = timing.intervention_step;
  const lead = Math.max(2, Math.round(2 * Number($("mu").value)));
  const start = peak ? (takeoff || Math.max(1, peak - lead)) : null;
  const cascade = (state.data && state.data.series && state.data.series.cascade) || [];
  const peakValue = cascade.length ? Math.max(...cascade) : 0;
  const repeats = (state.data && state.data.spec && state.data.spec.repeats) || Number($("repeats").value) || 0;
  const ja = I18N.lang === "ja";
  let windowText;
  if (peak && intervention) {
    windowText = ja
      ? `推奨される介入ウィンドウはステップ ${Math.max(1, peak - lead)}–${peak} です。ピークの約${lead}ステップ前（約2反応周期）で、今回の設定はステップ ${intervention} です。`
      : `Ein simuliertes Fenster liegt bei den Schritten ${Math.max(1, peak - lead)}–${peak}: etwa ${lead} Schritte vor dem Kaskadenpeak (rund zwei Reaktionszyklen). Dieser Lauf greift in Schritt ${intervention} ein.`;
  } else if (peak) {
    windowText = ja
      ? `ステップ ${start}–${peak} を重点的に見てください。カスケードは約ステップ ${start} で立ち上がり、ステップ ${peak} でピークになります（約${(peakValue * 100).toFixed(0)}%が同時に立場を変える）。`
      : `Schritte ${start}–${peak} beobachten: Die Kaskade beginnt etwa bei Schritt ${start} und erreicht bei Schritt ${peak} ihren Höhepunkt (${(peakValue * 100).toFixed(0)} % wechseln gleichzeitig).`;
  } else {
    windowText = ja
      ? "明瞭なカスケードは観測されませんでした。まずパラメータとトポロジーを確認してください。"
      : "Es wurde keine klare Kaskade beobachtet; zuerst Parameter und Topologie prüfen.";
  }
  if (consensus !== null && consensus !== undefined) {
    windowText += ja
      ? ` 約ステップ ${consensus} で多数に達します。`
      : ` Eine Mehrheit wird etwa bei Schritt ${consensus} erreicht.`;
  }
  const followups = ja
    ? [
        "今回のパラメータを基準にし、時点を1つだけ変えて再実行してください。2つの95% CIが重ならない場合にのみ「時点が有効」と判断できます。",
        `複製回数を30以上に増やしてから再確認してください（現在は${repeats}回）。区間が広い可能性があります。`,
        "実データで q、遅延、初期態度分布を調整してください。ここでの時点はシミュレーション上の窓であり、事象予測ではありません。",
      ]
    : [
        "Diesen Lauf als Basis nehmen, nur ein Timing ändern und erneut ausführen; erst wenn sich die beiden 95 %-KIs nicht überlappen, ist der Zeitpunkt belegt.",
        `Replikate vor der Entscheidung auf 30+ erhöhen (aktuell ${repeats}); das Intervall kann breit sein.`,
        "q, Latenz und Anfangsverteilung an echten Daten kalibrieren; das Fenster ist simuliert, keine Ereignisprognose.",
      ];
  if (state.data && state.data.metrics && state.data.metrics.absorbing
      && state.data.metrics.absorbing.mean >= 0.5) {
    followups.push(ja
      ? "合意を遅らせたい場合は、遅延を長くするか q を下げて、窓が後ろにずれるか確認してください。"
      : "Wenn das Ziel ist, den Konsens zu verzögern, längere Latenz oder ein niedrigeres q testen und prüfen, ob das Fenster später liegt.");
  }
  return {
    decisionText: I18N.template(currentTemplate(), "decision"),
    windowText,
    followups,
    caveat: ja
      ? "時点の提案は所定の仮定に基づくシミュレーションであり、実イベントの時刻予測ではありません。"
      : "Zeitangaben stammen aus einer Simulation unter Annahmen und sind keine Prognose realer Ereigniszeitpunkte.",
  };
}

function renderDecision(decision) {
  const panel = $("decision");
  if (!panel) return;
  if (!decision) { panel.hidden = true; return; }
  panel.hidden = false;
  const localized = I18N.lang === "ja" || I18N.lang === "de" ? decisionCopy(decision) : null;
  const timing = decision.timing || {};
  const labels = [
    ["takeoff_step", P("起势", "take-off", "立ち上がり", "Anlauf")],
    ["peak_step", P("峰值", "peak", "ピーク", "Peak")],
    ["consensus_step", P("多数", "majority", "多数", "Mehrheit")],
    ["intervention_step", P("干预", "intervention", "介入", "Eingriff")],
  ];
  const stepLabel = T("stepLabel");
  text("decisionText", localized ? localized.decisionText : P(decision.decision_zh, decision.decision_en));
  if ($("timing")) {
    $("timing").innerHTML = labels
      .filter(([key]) => timing[key] !== null && timing[key] !== undefined)
      .map(([key, label]) => `<span class="chip-timing">${label} <b>${stepLabel} ${timing[key]}</b></span>`)
      .join("");
  }
  text("window", localized ? localized.windowText : P(decision.window_zh, decision.window_en));
  const followups = localized ? localized.followups : P(decision.followups_zh, decision.followups_en);
  if ($("followups")) $("followups").innerHTML = followups.map((item) => `<li>${item}</li>`).join("");
  text("caveat", localized ? localized.caveat : P(decision.caveat_zh, decision.caveat_en));
}

function renderPlain(data) {
  const m = data.metrics || {};
  const diversity = m.diversity_final ? m.diversity_final.mean : null;
  const absorbing = m.absorbing ? m.absorbing.mean : null;
  const consensus = m.time_to_consensus ? m.time_to_consensus.mean : null;
  const cascade = (data.series && data.series.cascade) || [];
  const peak = cascade.length ? Math.max(...cascade) : 0;
  const peakStep = cascade.length ? cascade.indexOf(peak) + 1 : 0;
  const bullets = [];
  if (diversity !== null && diversity !== undefined) {
    bullets.push(P(
      `最终多样性 ${fmt(diversity)}：${diversity < 0.05 ? "基本只剩一种声音" : diversity < 0.2 ? "仍有少数派，但明显收拢" : "多种立场仍然并存"}。`,
      `Final diversity ${fmt(diversity)}: ${diversity < 0.05 ? "one stance dominates" : diversity < 0.2 ? "minority remains but shrinking" : "multiple stances still coexist"}.`,
      `最終的な多様性 ${fmt(diversity)}：${diversity < 0.05 ? "ほぼ一つの声だけ" : diversity < 0.2 ? "少数派は残るが縮小" : "複数の立場が併存"}。`,
      `Endgültige Diversität ${fmt(diversity)}: ${diversity < 0.05 ? "eine Haltung dominiert" : diversity < 0.2 ? "Minderheit bleibt, schrumpft aber" : "mehrere Haltungen bestehen weiter"}.`,
    ));
  }
  if (cascade.length) {
    bullets.push(P(
      `级联峰值在第 ${peakStep} 步，约 ${(peak * 100).toFixed(0)}% 的人同时改变立场。`,
      `The cascade peaked at step ${peakStep}; about ${(peak * 100).toFixed(0)}% changed at once.`,
      `カスケードのピークはステップ ${peakStep} で、約${(peak * 100).toFixed(0)}%が同時に立場を変えました。`,
      `Der Kaskadenpeak lag bei Schritt ${peakStep}; etwa ${(peak * 100).toFixed(0)} % wechselten gleichzeitig.`,
    ));
  }
  if (consensus !== null && consensus !== undefined) {
    bullets.push(P(
      `约第 ${consensus.toFixed(1)} 步达到 80% 多数（只统计达到多数的副本）。`,
      `An 80% majority is reached around step ${consensus.toFixed(1)} (majority-reaching replicas only).`,
      `約ステップ ${consensus.toFixed(1)} で80%の多数に達します（多数に達した複製のみ）。`,
      `Eine 80 %-Mehrheit wird etwa bei Schritt ${consensus.toFixed(1)} erreicht (nur Replikate mit Mehrheit).`,
    ));
  } else {
    bullets.push(P(
      "本次没有副本在观测窗口内达到 80% 多数；这是截断（censoring），不是零。",
      "No replica reached an 80% majority inside the window; this is censoring, not zero.",
      "今回の観測窓内で80%の多数に達した複製はありません。これは打ち切りであり、ゼロではありません。",
      "Kein Replikat erreichte innerhalb des Fensters eine 80 %-Mehrheit; das ist Zensierung, nicht null.",
    ));
  }
  if (absorbing !== null && absorbing !== undefined) {
    bullets.push(P(
      `${(absorbing * 100).toFixed(0)}% 的副本最终稳定在多数。`,
      `${(absorbing * 100).toFixed(0)}% of replicas end in a stable majority.`,
      `${(absorbing * 100).toFixed(0)}%の複製が最終的に安定した多数に至りました。`,
      `${(absorbing * 100).toFixed(0)} % der Replikate enden in einer stabilen Mehrheit.`,
    ));
  }
  if ($("plainReading")) {
    $("plainReading").innerHTML =
      `<strong>${P("用一句话说：", "In plain words:", "ひと言でいうと：", "In einfachen Worten:")}</strong><ul>${bullets.map((item) => `<li>${item}</li>`).join("")}</ul>`;
  }
}

function summaryCopy(data) {
  const series = data.series;
  const start = series.diversity[0];
  const end = series.diversity[series.diversity.length - 1];
  const timing = (data.decision && data.decision.timing) || {};
  const peakStep = timing.peak_step || (series.cascade.length ? series.cascade.indexOf(Math.max(...series.cascade)) + 1 : 0);
  const peak = series.cascade.length ? Math.max(...series.cascade) : 0;
  const ttc = timing.consensus_step;
  const observed = series.steps.length ? series.steps[series.steps.length - 1] : series.diversity.length - 1;
  const stable = Boolean(data.metrics && data.metrics.absorbing && data.metrics.absorbing.mean >= 0.5);
  const ja = I18N.lang === "ja";
  const verdict = stable
    ? (ja ? "安定した合意" : "Stabiler Konsens")
    : ttc !== null && ttc !== undefined
      ? (ja ? "多数に達したが変化中" : "Mehrheit erreicht, weiter in Bewegung")
      : (ja ? "未収束" : "Nicht konvergiert");
  const textBody = ttc !== null && ttc !== undefined
    ? (ja
        ? `この仮定の下で、多様性は ${start.toFixed(2)} から ${end.toFixed(2)} に低下し、約ステップ ${ttc} で多数に達しました。カスケードのピークはステップ ${peakStep} で、約${(peak * 100).toFixed(0)}%が同時に立場を変えました。`
        : `Unter diesen Annahmen sank die Diversität von ${start.toFixed(2)} auf ${end.toFixed(2)}; eine Mehrheit wurde etwa bei Schritt ${ttc} erreicht. Der Kaskadenpeak lag bei Schritt ${peakStep}, wobei etwa ${(peak * 100).toFixed(0)} % gleichzeitig ihre Haltung änderten.`)
    : (ja
        ? `この仮定の下で、多様性は ${start.toFixed(2)} から ${end.toFixed(2)} に変化しましたが、${observed} ステップ以内に多数には達しませんでした。カスケードのピークはステップ ${peakStep}（${(peak * 100).toFixed(0)}%）です。`
        : `Unter diesen Annahmen bewegte sich die Diversität von ${start.toFixed(2)} auf ${end.toFixed(2)}, aber innerhalb von ${observed} Schritten wurde keine Mehrheit erreicht. Der Kaskadenpeak lag bei Schritt ${peakStep} (${(peak * 100).toFixed(0)} %).`);
  return { verdict, text: textBody };
}

function renderViews(data) {
  const summary = data.summary_text || {};
  const localized = I18N.lang === "ja" || I18N.lang === "de" ? summaryCopy(data) : null;
  if ($("verdict")) {
    $("verdict").textContent = localized
      ? localized.verdict
      : P(summary.verdict_zh || "", summary.verdict_en || "");
    const stable = Boolean(data.metrics && data.metrics.absorbing && data.metrics.absorbing.mean >= 0.5);
    $("verdict").className = stable ? "verdict good" : "verdict";
  }
  text("summary", localized ? localized.text : P(summary.text_zh || "", summary.text_en || ""));
  renderMetrics(data.metrics);
  renderPlain(data);
  renderDecision(data.decision);
  renderQuality(data);
  renderCharts(data);
  if ($("scrub")) {
    $("scrub").disabled = false;
    $("scrub").max = String(data.series.steps.length - 1);
    $("scrub").value = String(data.series.steps.length - 1);
  }
  if ($("play")) $("play").disabled = false;
  if ($("csv")) $("csv").disabled = false;
  if ($("download")) {
    $("download").hidden = IS_STATIC;
    $("download").disabled = IS_STATIC;
  }
  if ($("copy")) $("copy").disabled = false;
  if ($("compare")) {
    $("compare").disabled = !state.previous;
    $("compare").setAttribute("aria-pressed", String(Boolean(state.previous) && state.showPrevious));
    $("compare").classList.toggle("active", Boolean(state.previous) && state.showPrevious);
  }
  if ($("aiRun")) {
    if (IS_STATIC) {
      const card = document.querySelector(".ai-card");
      if (card) card.hidden = true;
    } else {
      const enabled = Boolean(state.features.ollama);
      $("aiRun").disabled = !enabled;
      text("aiStatus", enabled ? "" : T("aiDisabled"));
    }
  }
  updateInstrumentFromData(data);
  if (tracker) {
    tracker.setData({
      shares: data.series.shares[data.series.shares.length - 1],
      steps: data.series.steps.length,
      peak: Math.max(...data.series.cascade),
      divergence: data.metrics.diversity_final ? data.metrics.diversity_final.mean : 0,
    });
    text("trackStatus", T("trackLocked"));
    text("trackNodes", String((data.quality && data.quality.graph && data.quality.graph.n_nodes) || 150));
  }
}

function render(data, options) {
  const preview = Boolean(options && options.preview);
  // A preview must not become the comparison baseline: otherwise the first
  // real run would "compare" against the same parameters and always overlap.
  if (!preview && state.last) state.previous = state.last;
  if (!preview) state.last = data;
  state.data = data;
  state.preview = preview;
  if (!preview) state.showPrevious = true;
  renderViews(data);
  if (!preview) {
    renderDelta();
    updateURL();
  }
}

function renderFieldStats(series) {
  const diversity = series.diversity || [];
  const cascade = series.cascade || [];
  const shares = series.shares && series.shares.length ? series.shares[series.shares.length - 1] : [0.5, 0.5];
  if ($("fieldWaveStat") && diversity.length) {
    const max = Math.max(...diversity);
    const step = diversity.indexOf(max) + 1;
    text("fieldWaveStat", P(
      `峰值 ${max.toFixed(2)} @ S${step} · 当前 ${diversity[diversity.length - 1].toFixed(2)}`,
      `peak ${max.toFixed(2)} @ S${step} · now ${diversity[diversity.length - 1].toFixed(2)}`,
      `ピーク ${max.toFixed(2)} @ S${step} · 現在 ${diversity[diversity.length - 1].toFixed(2)}`,
      `Peak ${max.toFixed(2)} @ S${step} · aktuell ${diversity[diversity.length - 1].toFixed(2)}`,
    ));
  }
  if ($("fieldBarsStat") && cascade.length) {
    const max = Math.max(...cascade);
    const step = cascade.indexOf(max) + 1;
    text("fieldBarsStat", P(
      `峰值 ${(max * 100).toFixed(0)}% @ S${step}`,
      `peak ${(max * 100).toFixed(0)}% @ S${step}`,
      `ピーク ${(max * 100).toFixed(0)}% @ S${step}`,
      `Peak ${(max * 100).toFixed(0)} % @ S${step}`,
    ));
  }
  if ($("fieldCloudStat") && shares.length) {
    text("fieldCloudStat", P(
      `立场 0 ${(shares[0] * 100).toFixed(0)}% · 立场 1 ${(shares[1] * 100).toFixed(0)}%`,
      `stance 0 ${(shares[0] * 100).toFixed(0)}% · stance 1 ${(shares[1] * 100).toFixed(0)}%`,
      `立場 0 ${(shares[0] * 100).toFixed(0)}% · 立場 1 ${(shares[1] * 100).toFixed(0)}%`,
      `Haltung 0 ${(shares[0] * 100).toFixed(0)} % · Haltung 1 ${(shares[1] * 100).toFixed(0)} %`,
    ));
  }
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
    ? P("置信区间重叠，暂时不能说明有差异", "CIs overlap, no clear difference", "信頼区間が重なり、差異はまだ判断できません", "KIs überlappen, kein klarer Unterschied")
    : diff > 0 ? P("比上一次更分散", "more diverse than the previous run", "前回より多様", "diverser als der vorherige Lauf")
               : P("比上一次更集中", "more concentrated than the previous run", "前回より集中", "konzentrierter als der vorherige Lauf");
  if ($("delta")) {
    $("delta").className = `delta ${cls}`;
    $("delta").textContent = P(
      `与上一次相比，多样性 ${diff >= 0 ? "+" : ""}${diff.toFixed(4)}；${verdict}`,
      `Diversity ${diff >= 0 ? "+" : ""}${diff.toFixed(4)} vs the previous run; ${verdict}.`,
      `前回との比較：多様性 ${diff >= 0 ? "+" : ""}${diff.toFixed(4)}。${verdict}。`,
      `Diversität ${diff >= 0 ? "+" : ""}${diff.toFixed(4)} gegenüber dem vorherigen Lauf; ${verdict}.`,
    );
  }
}

function updateURL() {
  const params = new URLSearchParams(requestBody());
  params.set("template", $("template").value);
  params.set("lang", I18N.lang);
  history.replaceState(null, "", `${location.pathname}?${params.toString()}`);
}

function shareUrl() {
  const url = new URL(location.href);
  const params = new URLSearchParams(requestBody());
  params.set("template", $("template").value);
  params.set("lang", I18N.lang);
  url.search = params.toString();
  return url.toString();
}

function showRunStatus(spec, preview) {
  const steps = spec.steps ?? spec.n_steps ?? 0;
  text("status", P(
    `${preview ? "预览" : "已完成"}：q=${spec.q} · ${steps} 步 · ${spec.repeats} 副本 · seed=${spec.seed}`,
    `${preview ? "Preview" : "Done"}: q=${spec.q} · ${steps} steps · ${spec.repeats} replicas · seed=${spec.seed}`,
    `${preview ? "プレビュー" : "完了"}：q=${spec.q} · ${steps}ステップ · ${spec.repeats}複製 · seed=${spec.seed}`,
    `${preview ? "Vorschau" : "Fertig"}: q=${spec.q} · ${steps} Schritte · ${spec.repeats} Replikate · Seed=${spec.seed}`,
  ));
}

async function simulate() {
  if (IS_STATIC) {
    if (!window.OpinionSim) throw new Error("browser simulator is not loaded");
    const settings = staticSettings();
    const result = OpinionSim.runMany(settings, settings.repeats);
    return OpinionSim.payload(settings, result, currentTemplate());
  }
  const response = await fetch(`${API_BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody()),
  });
  const payload = await response.json();
  if (!response.ok || payload.error) {
    throw new Error(payload.error?.message || `request failed (${response.status})`);
  }
  return payload.data;
}

async function run(options) {
  const preview = Boolean(options && options.preview);
  stopPlayback();
  if ($("error")) $("error").textContent = "";
  if ($("loading")) $("loading").hidden = false;
  if ($("run")) {
    $("run").classList.add("running");
    $("run").disabled = true;
  }
  text("status", T("running"));
  try {
    // Let the loading state paint before a synchronous browser simulation.
    await new Promise((resolve) => requestAnimationFrame(() => resolve()));
    const data = await simulate();
    render(data, { preview });
    showRunStatus(data.spec || {}, preview);
  } catch (error) {
    if ($("error")) $("error").textContent = error.message;
    text("status", "");
  } finally {
    if ($("run")) {
      $("run").disabled = false;
      $("run").classList.remove("running");
    }
    if ($("loading")) $("loading").hidden = true;
  }
}

function stopPlayback() {
  if (state.playRaf) cancelAnimationFrame(state.playRaf);
  if (state.scrubRaf) cancelAnimationFrame(state.scrubRaf);
  state.playRaf = null;
  state.scrubRaf = null;
  window.__OPINIONLAB_PLAYBACK__ = false;
}

function play() {
  if (!state.data) return;
  stopPlayback();
  const total = state.data.series.steps.length - 1;
  if (total <= 0) return;
  state.index = 0;
  if ($("scrub")) $("scrub").value = "0";
  window.__OPINIONLAB_PLAYBACK__ = true;
  renderCharts(state.data, 0, { playback: true });
  const started = performance.now();
  // 33 ms per step targets 30 fps, a readable pace that still looks smooth.
  // The index is derived from elapsed time, so a slow device skips steps
  // instead of building an unbounded backlog.
  const stepMs = 33;
  const tick = (now) => {
    if (!state.data) { state.playRaf = null; return; }
    const currentTotal = state.data.series.steps.length - 1;
    const index = Math.min(currentTotal, Math.floor((now - started) / stepMs));
    if (index !== state.index) {
      state.index = index;
      if ($("scrub")) $("scrub").value = String(index);
      renderCharts(state.data, index, { playback: true });
    }
    if (index < currentTotal) {
      state.playRaf = requestAnimationFrame(tick);
    } else {
      state.playRaf = null;
      window.__OPINIONLAB_PLAYBACK__ = false;
      // Restore the full option once so the final frame keeps every marker.
      renderCharts(state.data, currentTotal);
    }
  };
  state.playRaf = requestAnimationFrame(tick);
}

function downloadCsv() {
  if (!state.data) return;
  const series = state.data.series;
  const rows = [["step", "diversity", "cascade", ...series.shares[0].map((_, index) => `share${index}`)]];
  series.steps.forEach((step, index) => {
    rows.push([
      step,
      series.diversity[index],
      series.cascade[index],
      ...series.shares[index].map((value) => value),
    ]);
  });
  const blob = new Blob([rows.map((row) => row.join(",")).join("\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `opinionlab-${($("template") && $("template").value) || "run"}.csv`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

async function downloadReport() {
  if (IS_STATIC || !state.data) return;
  text("status", T("statusBuildingReport"));
  const response = await fetch(`${API_BASE}/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dataRequestBody()),
  });
  if (!response.ok) {
    if ($("error")) $("error").textContent = T("reportFailed");
    return;
  }
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `opinionlab-${$("template").value}-report.html`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  text("status", "");
}

async function runAi() {
  if (!state.data || !state.features.ollama || IS_STATIC) return;
  if ($("error")) $("error").textContent = "";
  text("aiStatus", T("aiRunning"));
  text("aiText", "");
  if ($("aiRun")) $("aiRun").disabled = true;
  try {
    const narrationLang = I18N.lang;
    const response = await fetch(`${API_BASE}/narrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...dataRequestBody(), lang: narrationLang }),
    });
    const payload = await response.json();
    if (!response.ok) {
      const code = payload.error?.code;
      if (code === "OLLAMA_DISABLED") throw new Error(T("aiDisabled"));
      throw new Error(payload.error?.message || T("aiFailed"));
    }
    const disclaimer = payload.data[`disclaimer_${narrationLang}`] || payload.data.disclaimer_en;
    text("aiText", `${payload.data.text}\n\n${disclaimer}`);
    text("aiStatus", `${payload.data.model} · ${T("aiAssistLabel")}`);
  } catch (error) {
    text("aiStatus", error.message);
  } finally {
    if ($("aiRun")) $("aiRun").disabled = false;
  }
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(shareUrl());
    text("status", T("statusCopied"));
  } catch {
    text("status", location.href);
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
    if (preset.steps) $("steps").value = Math.min(preset.steps, Number($("steps").max));
    if (preset.repeats) $("repeats").value = Math.min(preset.repeats, Number($("repeats").max));
    if (preset.q) { $("q").value = preset.q; updateLabels(); updateRange(); }
    if (preset.mu) $("mu").value = preset.mu;
    run({ preview: false });
  };
});

if ($("reset")) {
  $("reset").onclick = () => {
    applyTemplate(currentTemplate());
    run({ preview: false });
  };
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target.tagName !== "BUTTON" && !event.metaKey && !event.ctrlKey) {
    event.preventDefault();
    run({ preview: false });
  }
  if (event.key === "Escape") stopPlayback();
});

if ($("q")) $("q").oninput = () => { updateLabels(); updateRange(); };
if ($("template")) {
  $("template").onchange = () => {
    applyTemplate(currentTemplate());
    run({ preview: true });
  };
}
if ($("run")) $("run").onclick = () => run({ preview: false });
if ($("heroRun")) {
  $("heroRun").addEventListener("click", (event) => {
    event.preventDefault();
    const controls = $("controls");
    if (controls) controls.scrollIntoView({ behavior: "smooth", block: "start" });
    if (state.templates.length && $("run") && !$("run").disabled) $("run").click();
  });
}
if ($("play")) $("play").onclick = play;
if ($("scrub")) {
  $("scrub").oninput = () => {
    stopPlayback();
    if (!state.data) return;
    const index = Number($("scrub").value);
    if (state.scrubRaf) cancelAnimationFrame(state.scrubRaf);
    state.scrubRaf = requestAnimationFrame(() => {
      state.scrubRaf = null;
      if (state.data) renderCharts(state.data, index, { playback: true });
    });
  };
}
if ($("csv")) $("csv").onclick = downloadCsv;
if ($("download")) $("download").onclick = downloadReport;
if ($("copy")) $("copy").onclick = copyLink;
if ($("compare")) {
  $("compare").onclick = () => {
    if (!state.previous || !state.data) return;
    state.showPrevious = !state.showPrevious;
    $("compare").setAttribute("aria-pressed", String(state.showPrevious));
    $("compare").classList.toggle("active", state.showPrevious);
    renderCharts(state.data);
  };
}
if ($("aiRun")) $("aiRun").onclick = runAi;
window.addEventListener("resize", () => eachChart((chart) => chart.resize()));

window.addEventListener("languagechange", () => {
  refreshOptions();
  showQuestion();
  updateLabels();
  tickClock();
  if (footerMode) footerMode.textContent = T(IS_STATIC ? "footerStatic" : "footerApiMode");
  if (state.data) {
    renderViews(state.data);
    renderDelta();
    showRunStatus(state.data.spec || {}, state.preview);
  }
  if ($("aiText")) $("aiText").textContent = "";
});
if ($("langToggle")) {
  $("langToggle").addEventListener("change", (event) => I18N.setLang(event.target.value));
}

/* One fixed-position tooltip layer, so help text is never clipped by the
   scrollable control rail or by the viewport edge. */
const tooltip = $("siteTooltip");
let tooltipOwner = null;

function hideTooltip() {
  tooltipOwner = null;
  if (tooltip) tooltip.hidden = true;
}

function showTooltip(button) {
  if (!tooltip) return;
  const value = button.dataset.tip || "";
  if (!value) return;
  tooltipOwner = button;
  tooltip.textContent = value;
  tooltip.hidden = false;
  const rect = button.getBoundingClientRect();
  const margin = 8;
  const width = tooltip.offsetWidth;
  const height = tooltip.offsetHeight;
  let left = rect.right - width;
  left = Math.max(margin, Math.min(left, window.innerWidth - width - margin));
  let top = rect.bottom + 6;
  if (top + height > window.innerHeight - margin) top = rect.top - height - 6;
  top = Math.max(margin, top);
  tooltip.style.left = `${Math.round(left)}px`;
  tooltip.style.top = `${Math.round(top)}px`;
}

document.querySelectorAll(".help").forEach((button) => {
  button.addEventListener("mouseenter", () => showTooltip(button));
  button.addEventListener("focus", () => showTooltip(button));
  button.addEventListener("click", (event) => {
    event.preventDefault();
    if (tooltipOwner === button) hideTooltip();
    else showTooltip(button);
  });
  button.addEventListener("mouseleave", hideTooltip);
  button.addEventListener("blur", hideTooltip);
});
window.addEventListener("scroll", hideTooltip, true);
window.addEventListener("languagechange", () => {
  if (tooltipOwner) showTooltip(tooltipOwner);
});

const footerMode = $("footerMode");
if (footerMode) footerMode.textContent = T(IS_STATIC ? "footerStatic" : "footerApiMode");
if ($("apiDocsLink") && IS_STATIC) $("apiDocsLink").hidden = true;
if (IS_STATIC) {
  if ($("download")) $("download").hidden = true;
  const aiCard = document.querySelector(".ai-card");
  if (aiCard) aiCard.hidden = true;
}

loadTemplates()
  .then(() => {
    updateRange();
    const params = new URLSearchParams(location.search);
    if (params.get("autorun") === "0") {
      showQuestion();
      updateLabels();
      return;
    }
    run({ preview: params.get("run") !== "1" });
  })
  .catch((error) => {
    if ($("error")) $("error").textContent = error.message;
  });
