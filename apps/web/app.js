const $ = (id) => document.getElementById(id);
const T = (key) => (window.I18N ? I18N.t(key) : key);
const P = (zh, en, ja, de) => (window.I18N ? I18N.pick(zh, en, ja, de) : zh);
const state = {
  templates: [],
  features: {},
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
if (window.TrackGalaxy && $("galaxyScene")) TrackGalaxy.create($("galaxyScene"));

const fields = [];
if (window.TrackField) {
  [["fieldWave", "wave"], ["fieldBars", "bars"], ["fieldCloud", "cloud"]].forEach(([id, mode]) => {
    if ($(id)) fields.push(TrackField.create($(id), mode));
  });
}

const particleFields = [];
function addParticles(id, chart, mode) {
  if (window.TrackParticles && $(id)) particleFields.push(TrackParticles.create($(id), chart, mode));
}
addParticles("particlesDiversity", charts.diversity, "line");
addParticles("particlesShares", charts.shares, "shares");
addParticles("particlesCascade", charts.cascade, "cascade");

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
      $("trackStep").textContent = String(step).padStart(3, "0");
      $("trackDiv").textContent = divergence.toFixed(2);
      if (active) $("trackStatus").textContent = P("已锁定", "LOCKED", "ロック済み", "ERFASST");
    },
  });
  $("trackNodes").textContent = "150";
}
const AXIS = { axisLine: { lineStyle: { color: "#1e4a5f" } }, axisLabel: { color: "#7fa6bd", fontSize: 9, fontFamily: "ui-monospace" } };
const SPLIT = { lineStyle: { color: "rgba(30,74,95,.55)" } };

const METRICS = ["diversity_final", "cascade_p99", "time_to_consensus", "absorbing"];

const METRIC_LABELS = {
  diversity_final: ["多样性", "Diversity", "多様性", "Diversität"],
  cascade_p99: ["级联 P99", "Cascade P99", "カスケード P99", "Kaskade P99"],
  time_to_consensus: ["收敛步", "Consensus step", "合意到達ステップ", "Konsensschritt"],
  absorbing: ["吸收态比例", "Absorbing rate", "吸収率", "Absorptionsrate"],
};

function fmt(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value !== "number") return String(value);
  return Math.abs(value) >= 10 ? value.toFixed(1) : value.toFixed(3);
}

function updateLabels() {
  const value = Number($("q").value).toFixed(1);
  $("qVal").textContent = value;
  if ($("qScaleValue")) $("qScaleValue").textContent = value;
}

function currentTemplate() {
  return state.templates.find((item) => item.key === $("template").value);
}

function showQuestion() {
  const template = currentTemplate();
  if (!template) return;
  $("question").innerHTML = I18N.template(template, "question");
  $("reading").innerHTML =
    `<strong>${T("readPrefix")}</strong> ${I18N.template(template, "interpretation")}`;
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
  const clamped = Math.max(0, Math.min(100, Number(value) || 0));
  wrap.style.setProperty("--gauge", clamped.toFixed(1));
  output.textContent = String(Math.round(clamped));
}

function updateInstrumentFromData(data) {
  if (!$("heroSteps") || !data) return;
  const metrics = data.metrics || {};
  const diversityMetric = metrics.diversity_final || {};
  const diversity = diversityMetric.mean;
  const cohesion = diversity === null || diversity === undefined ? 0 : (1 - Math.max(0, Math.min(1, diversity))) * 100;
  const cascade = (data.series && data.series.cascade) || [];
  const peak = cascade.length ? Math.max(...cascade) * 100 : 0;
  const consensus = metrics.time_to_consensus && metrics.time_to_consensus.mean;
  const n = diversityMetric.n || (data.spec && data.spec.repeats) || 0;
  const steps = data.series && data.series.steps ? Math.max(0, data.series.steps.length - 1) : (data.spec && data.spec.n_steps) || 0;
  const halfCi = diversityMetric.ci95_hi !== null && diversityMetric.ci95_hi !== undefined
    ? (diversityMetric.ci95_hi - diversityMetric.ci95_lo) / 2 : null;
  setGauge("gaugeCohesionWrap", "gaugeCohesion", cohesion);
  setGauge("gaugeTurnWrap", "gaugeTurn", peak);
  $("heroSteps").textContent = String(Math.round(steps));
  $("heroMajority").textContent = consensus === null || consensus === undefined ? "—" : consensus.toFixed(1);
  $("heroPeak").textContent = String(Math.round(peak));
  $("heroCi").textContent = halfCi === null ? "—" : `±${halfCi.toFixed(3)}`;
  if ($("heroRunMeta")) {
    $("heroRunMeta").textContent = P(
      `运行结果 // ${n} 个副本`,
      `LIVE RUN // ${n} REPLICAS`,
      `実行結果 // ${n} 複製`,
      `LIVE-LAUF // ${n} REPLIKATE`,
    );
  }
}

async function loadTemplates() {
  const response = await fetch("/api/v1/demo/templates");
  const payload = await response.json();
  state.templates = payload.data;
  state.features = payload.features || {};
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
    .map((item) => `<option value="${item.key}">${item.key} · ${I18N.template(item, "name")}</option>`)
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

const METRIC_WHY = {
  diversity_final: [
    "越低越集中；0 表示只剩一种立场。",
    "Lower is more concentrated; 0 means one stance left.",
    "低いほど集中しており、0 は一つの立場だけが残った状態です。",
    "Niedriger bedeutet konzentrierter; 0 heißt, dass nur eine Haltung übrig bleibt.",
  ],
  cascade_p99: [
    "最剧烈的 1% 步数里，改变立场的人占比。",
    "Share changing in the most intense 1% of steps.",
    "最も激しい1%のステップで、立場を変えた人の割合。",
    "Anteil der Wechsel in den intensivsten 1 % der Schritte.",
  ],
  time_to_consensus: [
    "达到 80% 多数所需的步数；只统计达到多数的副本。",
    "Steps to an 80% majority; majority-reaching replicas only.",
    "80%の多数に達するまでのステップ数。多数に達した複製のみを集計します。",
    "Schritte bis zu einer 80 %-Mehrheit; nur Replikate, die eine Mehrheit erreichen.",
  ],
  absorbing: [
    "有多少副本最终稳定在多数。",
    "Share of replicas that end in a stable majority.",
    "最終的に安定した多数に至った複製の割合。",
    "Anteil der Replikate, die in einer stabilen Mehrheit enden.",
  ],
};

function metricCard(key, label, metric) {
  const value = metric && metric.mean !== null && metric.mean !== undefined ? metric.mean : null;
  const ci = metric && metric.ci95_lo !== null && metric.ci95_lo !== undefined
    ? `95% CI ${fmt(metric.ci95_lo)} – ${fmt(metric.ci95_hi)} · n=${metric.n}`
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
      ? { xAxis: timing.takeoff_step, label: { formatter: P("起势", "take-off", "立ち上がり", "Anlauf"), position: "insideEndTop", rotate: 0 } }
      : null,
    timing.peak_step
      ? { xAxis: timing.peak_step, label: { formatter: P("峰值", "peak", "ピーク", "Peak"), position: "insideEndTop", rotate: 0 } }
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
              data: [P("本次运行", "this run", "今回の実行", "dieser Lauf"), P("中位数", "median", "中央値", "Median"), "10–90%"] },
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
      { name: P("中位数", "median", "中央値", "Median"), type: "line", data: sliceUpto(bands.p50, index),
        smooth: true, showSymbol: false, lineStyle: { type: "dashed", width: 1.4, color: "#ffb020" } },
      { name: P("本次运行", "this run", "今回の実行", "dieser Lauf"), type: "line", data: sliceUpto(series.diversity, index),
        smooth: true, showSymbol: false, lineStyle: { width: 2.4, color: "#22d3ee" },
        areaStyle: { color: runGradient } },
    ],
  });

  const opinionCount = data.opinion_count || 2;
  const shares = Array.from({ length: opinionCount }, (_, opinion) => ({
    name: P(`立场 ${opinion}`, `Opinion ${opinion}`, `立場 ${opinion}`, `Haltung ${opinion}`),
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
  return {
    decisionText: I18N.template(currentTemplate(), "decision"),
    windowText,
    followups: ja
      ? [
          "今回のパラメータを基準にし、時点を1つだけ変えて再実行してください。2つの95% CIが重ならない場合にのみ「時点が有効」と判断できます。",
          `複製回数を30以上に増やしてから再確認してください（現在は${repeats}回）。区間が広い可能性があります。`,
          "実データで q、遅延、初期態度分布を調整してください。ここでの時点はシミュレーション上の窓であり、事象予測ではありません。",
        ]
      : [
          "Diesen Lauf als Basis nehmen, nur ein Timing ändern und erneut ausführen; erst wenn sich die beiden 95 %-KIs nicht überlappen, ist der Zeitpunkt belegt.",
          `Replikate vor der Entscheidung auf 30+ erhöhen (aktuell ${repeats}); das Intervall kann breit sein.`,
          "q, Latenz und Anfangsverteilung an echten Daten kalibrieren; das Fenster ist simuliert, keine Ereignisprognose.",
        ],
    caveat: ja
      ? "時点の提案は所定の仮定に基づくシミュレーションであり、実イベントの時刻予測ではありません。"
      : "Zeitangaben stammen aus einer Simulation unter Annahmen und sind keine Prognose realer Ereigniszeitpunkte.",
  };
}

function renderDecision(decision) {
  const panel = $("decision");
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
  $("decisionText").textContent = localized ? localized.decisionText : P(decision.decision_zh, decision.decision_en);
  $("timing").innerHTML = labels
    .filter(([key]) => timing[key] !== null && timing[key] !== undefined)
    .map(([key, label]) => `<span class="chip-timing">${label} <b>${stepLabel} ${timing[key]}</b></span>`)
    .join("");
  $("window").textContent = localized ? localized.windowText : P(decision.window_zh, decision.window_en);
  const followups = localized ? localized.followups : P(decision.followups_zh, decision.followups_en);
  $("followups").innerHTML = followups.map((item) => `<li>${item}</li>`).join("");
  $("caveat").textContent = localized ? localized.caveat : P(decision.caveat_zh, decision.caveat_en);
}

function renderPlain(data) {
  const m = data.metrics;
  const diversity = m.diversity_final ? m.diversity_final.mean : null;
  const absorbing = m.absorbing ? m.absorbing.mean : null;
  const consensus = m.time_to_consensus ? m.time_to_consensus.mean : null;
  const cascade = data.series.cascade || [];
  const peak = cascade.length ? Math.max(...cascade) : 0;
  const peakStep = cascade.length ? cascade.indexOf(peak) + 1 : 0;
  const bullets = [];
  if (diversity !== null) {
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
  if (consensus !== null) {
    bullets.push(P(
      `约第 ${consensus.toFixed(1)} 步达到 80% 多数。`,
      `An 80% majority is reached around step ${consensus.toFixed(1)}.`,
      `約ステップ ${consensus.toFixed(1)} で80%の多数に達します。`,
      `Eine 80 %-Mehrheit wird etwa bei Schritt ${consensus.toFixed(1)} erreicht.`,
    ));
  }
  if (absorbing !== null) {
    bullets.push(P(
      `${(absorbing * 100).toFixed(0)}% 的副本最终稳定在多数。`,
      `${(absorbing * 100).toFixed(0)}% of replicas end in a stable majority.`,
      `${(absorbing * 100).toFixed(0)}%の複製が最終的に安定した多数に至りました。`,
      `${(absorbing * 100).toFixed(0)} % der Replikate enden in einer stabilen Mehrheit.`,
    ));
  }
  $("plainReading").innerHTML =
    `<strong>${P("用一句话说：", "In plain words:", "ひと言でいうと：", "In einfachen Worten:")}</strong><ul>${bullets.map((item) => `<li>${item}</li>`).join("")}</ul>`;
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
  const stable = Boolean(data.summary && data.summary.absorbing);
  const ja = I18N.lang === "ja";
  const verdict = stable
    ? (ja ? "安定した合意" : "Stabiler Konsens")
    : ttc !== null && ttc !== undefined
      ? (ja ? "多数に達したが変化中" : "Mehrheit erreicht, weiter in Bewegung")
      : (ja ? "未収束" : "Nicht konvergiert");
  const text = ttc !== null && ttc !== undefined
    ? (ja
        ? `この仮定の下で、多様性は ${start.toFixed(2)} から ${end.toFixed(2)} に低下し、約ステップ ${ttc} で多数に達しました。カスケードのピークはステップ ${peakStep} で、約${(peak * 100).toFixed(0)}%が同時に立場を変えました。`
        : `Unter diesen Annahmen sank die Diversität von ${start.toFixed(2)} auf ${end.toFixed(2)}; eine Mehrheit wurde etwa bei Schritt ${ttc} erreicht. Der Kaskadenpeak lag bei Schritt ${peakStep}, wobei etwa ${(peak * 100).toFixed(0)} % gleichzeitig ihre Haltung änderten.`)
    : (ja
        ? `この仮定の下で、多様性は ${start.toFixed(2)} から ${end.toFixed(2)} に変化しましたが、${observed} ステップ以内に多数には達しませんでした。カスケードのピークはステップ ${peakStep}（${(peak * 100).toFixed(0)}%）です。`
        : `Unter diesen Annahmen bewegte sich die Diversität von ${start.toFixed(2)} auf ${end.toFixed(2)}, aber innerhalb von ${observed} Schritten wurde keine Mehrheit erreicht. Der Kaskadenpeak lag bei Schritt ${peakStep} (${(peak * 100).toFixed(0)} %).`);
  return { verdict, text };
}

function renderViews(data) {
  const summary = data.summary_text;
  const localized = I18N.lang === "ja" || I18N.lang === "de" ? summaryCopy(data) : null;
  $("verdict").textContent = localized ? localized.verdict : P(summary.verdict_zh, summary.verdict_en);
  $("verdict").className = data.summary.absorbing ? "verdict good" : "verdict";
  $("summary").textContent = localized ? localized.text : P(summary.text_zh, summary.text_en);
  renderMetrics(data.metrics);
  renderPlain(data);
  renderDecision(data.decision);
  renderCharts(data);
  $("scrub").disabled = false;
  $("scrub").max = String(data.series.steps.length - 1);
  $("scrub").value = String(data.series.steps.length - 1);
  $("play").disabled = false;
  $("download").disabled = false;
  $("copy").disabled = false;
  $("compare").disabled = !state.previous;
  if ($("aiRun")) {
    const enabled = Boolean(state.features.ollama);
    $("aiRun").disabled = !enabled;
    $("aiStatus").textContent = enabled ? "" : T("aiDisabled");
  }
  updateInstrumentFromData(data);
  if (tracker) {
    tracker.setData({
      shares: data.series.shares[data.series.shares.length - 1],
      steps: data.series.steps.length,
      peak: Math.max(...data.series.cascade),
      divergence: data.summary.diversity_final,
    });
    $("trackStatus").textContent = P("已锁定", "LOCKED", "ロック済み", "ERFASST");
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

function renderFieldStats(series) {
  const diversity = series.diversity || [];
  const cascade = series.cascade || [];
  const shares = series.shares && series.shares.length ? series.shares[series.shares.length - 1] : [0.5, 0.5];
  if ($("fieldWaveStat") && diversity.length) {
    const max = Math.max(...diversity);
    const step = diversity.indexOf(max) + 1;
    $("fieldWaveStat").textContent = P(
      `峰值 ${max.toFixed(2)} @ S${step} · 当前 ${diversity[diversity.length - 1].toFixed(2)}`,
      `peak ${max.toFixed(2)} @ S${step} · now ${diversity[diversity.length - 1].toFixed(2)}`,
      `ピーク ${max.toFixed(2)} @ S${step} · 現在 ${diversity[diversity.length - 1].toFixed(2)}`,
      `Peak ${max.toFixed(2)} @ S${step} · aktuell ${diversity[diversity.length - 1].toFixed(2)}`,
    );
  }
  if ($("fieldBarsStat") && cascade.length) {
    const max = Math.max(...cascade);
    const step = cascade.indexOf(max) + 1;
    $("fieldBarsStat").textContent = P(
      `峰值 ${(max * 100).toFixed(0)}% @ S${step}`,
      `peak ${(max * 100).toFixed(0)}% @ S${step}`,
      `ピーク ${(max * 100).toFixed(0)}% @ S${step}`,
      `Peak ${(max * 100).toFixed(0)} % @ S${step}`,
    );
  }
  if ($("fieldCloudStat") && shares.length) {
    $("fieldCloudStat").textContent = P(
      `立场 0 ${(shares[0] * 100).toFixed(0)}% · 立场 1 ${(shares[1] * 100).toFixed(0)}%`,
      `stance 0 ${(shares[0] * 100).toFixed(0)}% · stance 1 ${(shares[1] * 100).toFixed(0)}%`,
      `立場 0 ${(shares[0] * 100).toFixed(0)}% · 立場 1 ${(shares[1] * 100).toFixed(0)}%`,
      `Haltung 0 ${(shares[0] * 100).toFixed(0)} % · Haltung 1 ${(shares[1] * 100).toFixed(0)} %`,
    );
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
  $("delta").className = `delta ${cls}`;
  $("delta").textContent = P(
    `与上一次相比，多样性 ${diff >= 0 ? "+" : ""}${diff.toFixed(4)}；${verdict}`,
    `Diversity ${diff >= 0 ? "+" : ""}${diff.toFixed(4)} vs the previous run; ${verdict}.`,
    `前回との比較：多様性 ${diff >= 0 ? "+" : ""}${diff.toFixed(4)}。${verdict}。`,
    `Diversität ${diff >= 0 ? "+" : ""}${diff.toFixed(4)} gegenüber dem vorherigen Lauf; ${verdict}.`,
  );
}

function updateURL() {
  const params = new URLSearchParams(requestBody());
  params.set("template", $("template").value);
  params.set("lang", I18N.lang);
  history.replaceState(null, "", `${location.pathname}?${params.toString()}`);
}

function shareUrl() {
  const url = new URL(location.href);
  url.searchParams.set("lang", I18N.lang);
  return url.toString();
}

function showRunStatus(spec) {
  $("status").textContent = P(
    `q=${spec.q} · steps=${spec.n_steps} · ${spec.repeats} replicas · seed=${spec.seed}`,
    `q=${spec.q} · steps=${spec.n_steps} · ${spec.repeats} replicas · seed=${spec.seed}`,
    `q=${spec.q} · ステップ=${spec.n_steps} · ${spec.repeats} 複製 · シード=${spec.seed}`,
    `q=${spec.q} · Schritte=${spec.n_steps} · ${spec.repeats} Replikate · Seed=${spec.seed}`,
  );
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
    showRunStatus(payload.data.spec);
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
  $("status").textContent = T("statusBuildingReport");
  const response = await fetch("/api/v1/demo/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody()),
  });
  if (!response.ok) {
    $("error").textContent = T("reportFailed");
    return;
  }
  const blob = await response.blob();
  window.open(URL.createObjectURL(blob), "_blank");
  $("status").textContent = "";
}

async function runAi() {
  if (!state.data || !state.features.ollama) return;
  $("error").textContent = "";
  $("aiStatus").textContent = T("aiRunning");
  $("aiText").textContent = "";
  $("aiRun").disabled = true;
  try {
    const narrationLang = I18N.lang;
    const response = await fetch("/api/v1/demo/narrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...requestBody(), lang: narrationLang }),
    });
    const payload = await response.json();
    if (!response.ok) {
      const code = payload.error?.code;
      if (code === "OLLAMA_DISABLED") throw new Error(T("aiDisabled"));
      throw new Error(payload.error?.message || T("aiFailed"));
    }
    const disclaimer = payload.data[`disclaimer_${narrationLang}`] || payload.data.disclaimer_en;
    $("aiText").textContent = `${payload.data.text}\n\n${disclaimer}`;
    $("aiStatus").textContent = `${payload.data.model} · ${T("aiAssistLabel")}`;
  } catch (error) {
    $("aiStatus").textContent = error.message;
  } finally {
    $("aiRun").disabled = false;
  }
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(shareUrl());
    $("status").textContent = T("statusCopied");
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
if ($("heroRun")) {
  $("heroRun").addEventListener("click", (event) => {
    event.preventDefault();
    const controls = $("controls");
    if (controls) controls.scrollIntoView({ behavior: "smooth", block: "start" });
    if (state.templates.length && !$("run").disabled) $("run").click();
  });
}
$("play").onclick = play;
$("scrub").oninput = () => {
  stopPlayback();
  if (state.data) renderCharts(state.data, Number($("scrub").value));
};
$("download").onclick = download;
$("copy").onclick = copyLink;
if ($("aiRun")) $("aiRun").onclick = runAi;
window.addEventListener("resize", () => Object.values(charts).forEach((chart) => chart.resize()));

window.addEventListener("languagechange", () => {
  refreshOptions();
  showQuestion();
  updateLabels();
  tickClock();
  if (state.data) renderViews(state.data);
  if (state.last) renderDelta();
  if ($("aiText")) $("aiText").textContent = "";
  if (state.data) showRunStatus(state.data.spec);
});
if ($("langToggle")) {
  $("langToggle").addEventListener("change", (event) => I18N.setLang(event.target.value));
}

loadTemplates()
  .then(() => {
    updateRange();
    if (new URLSearchParams(location.search).get("run") === "1") run();
  })
  .catch((error) => { $("error").textContent = error.message; });
