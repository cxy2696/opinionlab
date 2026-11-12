const $ = (id) => document.getElementById(id);
const T = (key) => (window.I18N ? I18N.t(key) : key);
const P = (zh, en, ja, de) => (window.I18N ? I18N.pick(zh, en, ja, de) : zh);
const state = { templates: [], last: null, previous: null, config: null, timer: null, index: 0 };
const COLORS = ["#22d3ee", "#ffb020", "#34d399", "#a78bfa", "#fb7185"];
const charts = {
  diversity: echarts.init($("chartDiversity")),
  shares: echarts.init($("chartShares")),
  cascade: echarts.init($("chartCascade")),
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
    $("heroDate").textContent = `${pad(now.getDate())}-${pad(now.getMonth() + 1)}-${now.getFullYear()}`;
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
  const value = Number($("q").value).toFixed(1);
  $("qVal").textContent = value;
  if ($("qScaleValue")) $("qScaleValue").textContent = value;
}

function updateRange() {
  const input = $("q");
  const ratio = (Number(input.value) - Number(input.min)) / (Number(input.max) - Number(input.min));
  input.style.setProperty("--p", `${(ratio * 100).toFixed(1)}%`);
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
  if (!state.last && $("heroRunMeta")) {
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
  if (!$("heroSteps") || !data || !data.metrics) return;
  const m = data.metrics;
  const diversityMetric = m.diversity || {};
  const diversity = diversityMetric.mean;
  const cohesion = diversity === null || diversity === undefined ? 0 : (1 - Math.max(0, Math.min(1, diversity))) * 100;
  const peak = (m.peakValue || 0) * 100;
  const consensus = m.consensus ? m.consensus.mean : null;
  const n = diversityMetric.n || (state.config && state.config.repeats) || 0;
  const steps = state.config ? state.config.steps : (data.first && data.first.diversity ? data.first.diversity.length - 1 : 0);
  const halfCi = diversityMetric.hi !== null && diversityMetric.hi !== undefined
    ? (diversityMetric.hi - diversityMetric.lo) / 2 : null;
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
    .map((item) => `<option value="${item.key}">${item.key} · ${I18N.template(item, "name")}</option>`)
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
  diversity: [
    "越低越集中；0 表示只剩一种立场。",
    "Lower is more concentrated; 0 means one stance left.",
    "低いほど集中しており、0 は一つの立場だけが残った状態です。",
    "Niedriger bedeutet konzentrierter; 0 heißt, dass nur eine Haltung übrig bleibt.",
  ],
  peak: [
    "级联最剧烈的一步，多少人同时改变立场。",
    "The most intense step: how many changed at once.",
    "カスケードが最も激しい1ステップで、同時に立場を変えた人数。",
    "Der intensivste Schritt: Wie viele änderten gleichzeitig ihre Haltung?",
  ],
  consensus: [
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
    metricCard(P("多样性", "Diversity", "多様性", "Diversität"), m.diversity.mean, [m.diversity.lo, m.diversity.hi], false, P(...METRIC_WHY.diversity)),
    metricCard(P("级联峰值", "Peak cascade", "カスケードピーク", "Kaskadenpeak"), m.peakValue, null, false, P(...METRIC_WHY.peak)),
    metricCard(P("达到多数的步", "Majority step", "多数到達ステップ", "Mehrheitsschritt"), m.consensus ? m.consensus.mean : null, null, false, P(...METRIC_WHY.consensus)),
    metricCard(P("吸收比例", "Absorbing rate", "吸収率", "Absorptionsrate"), m.absorbing.rate, null, true, P(...METRIC_WHY.absorbing)),
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
    `最終的な多様性 ${fmt(diversity)}：${diversity < 0.05 ? "ほぼ一つの声だけ" : diversity < 0.2 ? "少数派は残るが縮小" : "複数の立場が併存"}。`,
    `Endgültige Diversität ${fmt(diversity)}: ${diversity < 0.05 ? "eine Haltung dominiert" : diversity < 0.2 ? "Minderheit bleibt, schrumpft aber" : "mehrere Haltungen bestehen weiter"}.`,
  ));
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
  bullets.push(P(
    `${(absorbing * 100).toFixed(0)}% 的副本最终稳定在多数。`,
    `${(absorbing * 100).toFixed(0)}% of replicas end in a stable majority.`,
    `${(absorbing * 100).toFixed(0)}%の複製が最終的に安定した多数に至りました。`,
    `${(absorbing * 100).toFixed(0)} % der Replikate enden in einer stabilen Mehrheit.`,
  ));
  $("plainReading").innerHTML =
    `<strong>${P("用一句话说：", "In plain words:", "ひと言でいうと：", "In einfachen Worten:")}</strong><ul>${bullets.map((item) => `<li>${item}</li>`).join("")}</ul>`;
}

function decisionCopy(decision) {
  const timing = decision.timing || {};
  const peak = timing.peak;
  const takeoff = timing.takeoff;
  const consensus = timing.consensus;
  const intervention = timing.intervention;
  const config = state.config || {};
  const lead = Math.max(2, Math.round(2 * Number(config.latency_mu || 1)));
  const start = peak ? (takeoff || Math.max(1, peak - lead)) : null;
  const cascade = (state.last && state.last.first && state.last.first.cascade) || [];
  const peakValue = cascade.length ? Math.max(...cascade) : 0;
  const repeats = Number(config.repeats || 0);
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
  const labels = [
    ["takeoff", P("起势", "take-off", "立ち上がり", "Anlauf")],
    ["peak", P("峰值", "peak", "ピーク", "Peak")],
    ["consensus", P("多数", "majority", "多数", "Mehrheit")],
    ["intervention", P("干预", "intervention", "介入", "Eingriff")],
  ];
  const stepLabel = T("stepLabel");
  $("decisionText").textContent = localized ? localized.decisionText : P(decision.decisionZh, decision.decisionEn);
  $("timing").innerHTML = labels
    .filter(([key]) => decision.timing[key] !== null && decision.timing[key] !== undefined)
    .map(([key, label]) => `<span class="chip-timing">${label} <b>${stepLabel} ${decision.timing[key]}</b></span>`)
    .join("");
  $("window").textContent = localized ? localized.windowText : P(decision.windowZh, decision.windowEn);
  $("followups").innerHTML = (localized ? localized.followups : P(decision.followupsZh, decision.followupsEn))
    .map((item) => `<li>${item}</li>`).join("");
  $("caveat").textContent = localized ? localized.caveat : P(decision.caveatZh, decision.caveatEn);
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
              data: [P("本次运行", "this run", "今回の実行", "dieser Lauf"), P("中位数", "median", "中央値", "Median"), "10–90%"] },
    grid: { left: 44, right: 14, top: 30, bottom: 26 },
    xAxis: { type: "category", data: steps, boundaryGap: false, ...AXIS, splitLine: { show: false } },
    yAxis: { type: "value", min: 0, max: 0.5, ...AXIS, splitLine: SPLIT },
    series: [
      { name: "下界", type: "line", stack: "band", data: slice(data.bands.p10, index),
        lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, symbol: "none", silent: true },
      { name: "10–90%", type: "line", stack: "band", data: slice(width, index),
        lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(34,211,238,.16)" }, symbol: "none", silent: true },
      { name: P("中位数", "median", "中央値", "Median"), type: "line", data: slice(data.bands.p50, index),
        smooth: true, showSymbol: false, lineStyle: { type: "dashed", width: 1.4, color: "#ffb020" } },
      { name: P("本次运行", "this run", "今回の実行", "dieser Lauf"), type: "line", data: slice(first.diversity, index),
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
      name: P(`立场 ${opinion}`, `Opinion ${opinion}`, `立場 ${opinion}`, `Haltung ${opinion}`),
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
      markLine: { symbol: "none", data: [{ xAxis: peak, label: { formatter: P("峰值", "peak", "ピーク", "Peak"), position: "insideEndTop", rotate: 0 } }] },
    }],
  });

  if (particleFields.length === 3) {
    particleFields[0].setData(first.diversity.slice(0, index + 1));
    particleFields[1].setData(first.shares.slice(0, index + 1));
    particleFields[2].setData(first.cascade.slice(0, index + 1));
  }
  if (fields.length === 3) {
    const payload = { diversity: first.diversity.slice(0, index + 1),
      cascade: first.cascade.slice(0, index + 1), shares: first.shares.slice(0, index + 1) };
    fields.forEach((field) => field.setData(payload));
    renderFieldStats(payload);
  }
}

function renderSummary(data) {
  const first = data.first;
  const start = first.diversity[0];
  const end = first.finalDiversity;
  const ttc = first.timeToConsensus;
  const stable = data.metrics.absorbing.rate >= 0.5;
  const verdict = stable ? P("形成稳定共识", "Stable consensus", "安定した合意", "Stabiler Konsens")
    : ttc >= 0 ? P("达到多数，但仍在变化", "Majority reached, still moving", "多数に達したが変化中", "Mehrheit erreicht, weiter in Bewegung")
               : P("尚未收敛", "Not converged", "未収束", "Nicht konvergiert");
  $("verdict").textContent = verdict;
  $("verdict").className = stable ? "verdict good" : "verdict";
  const observed = first.diversity.length - 1;
  const peakStep = data.metrics.peakStep;
  const peakShare = (data.metrics.peakValue * 100).toFixed(0);
  const zh = ttc >= 0
    ? `在这组假设下，多样性从 ${start.toFixed(2)} 降到 ${end.toFixed(2)}；约在第 ${ttc} 步达到多数。级联峰值在第 ${peakStep} 步（${peakShare}% 的人同时改变立场）。`
    : `在这组假设下，多样性从 ${start.toFixed(2)} 变到 ${end.toFixed(2)}，但在 ${observed} 步内没有达到多数。级联峰值在第 ${peakStep} 步。`;
  const en = ttc >= 0
    ? `Under these assumptions diversity fell from ${start.toFixed(2)} to ${end.toFixed(2)}, reaching a majority around step ${ttc}. The cascade peaked at step ${peakStep}, with about ${peakShare}% changing at once.`
    : `Diversity moved from ${start.toFixed(2)} to ${end.toFixed(2)} without a majority in ${observed} steps. The cascade peaked at step ${peakStep}.`;
  const ja = ttc >= 0
    ? `この仮定の下で、多様性は ${start.toFixed(2)} から ${end.toFixed(2)} に低下し、約ステップ ${ttc} で多数に達しました。カスケードのピークはステップ ${peakStep} で、約${peakShare}%が同時に立場を変えました。`
    : `この仮定の下で、多様性は ${start.toFixed(2)} から ${end.toFixed(2)} に変化しましたが、${observed} ステップ以内に多数には達しませんでした。カスケードのピークはステップ ${peakStep} です。`;
  const de = ttc >= 0
    ? `Unter diesen Annahmen sank die Diversität von ${start.toFixed(2)} auf ${end.toFixed(2)}; eine Mehrheit wurde etwa bei Schritt ${ttc} erreicht. Der Kaskadenpeak lag bei Schritt ${peakStep}, wobei etwa ${peakShare} % gleichzeitig ihre Haltung änderten.`
    : `Unter diesen Annahmen bewegte sich die Diversität von ${start.toFixed(2)} auf ${end.toFixed(2)}, aber innerhalb von ${observed} Schritten wurde keine Mehrheit erreicht. Der Kaskadenpeak lag bei Schritt ${peakStep}.`;
  $("summary").textContent = P(zh, en, ja, de);
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
  const before = state.previous.metrics.diversity;
  const after = state.last.metrics.diversity;
  const diff = after.mean - before.mean;
  const overlap = !(after.hi < before.lo || after.lo > before.hi);
  $("delta").className = `delta ${overlap ? "flat" : diff > 0 ? "up" : "down"}`;
  $("delta").textContent = P(
    `与上一次相比，多样性 ${diff >= 0 ? "+" : ""}${diff.toFixed(4)}；${overlap ? "置信区间重叠，差异不显著" : diff > 0 ? "更分散" : "更集中"}`,
    `Diversity ${diff >= 0 ? "+" : ""}${diff.toFixed(4)} vs the previous run; ${overlap ? "CIs overlap, no clear difference" : diff > 0 ? "more diverse" : "more concentrated"}.`,
    `前回との比較：多様性 ${diff >= 0 ? "+" : ""}${diff.toFixed(4)}。${overlap ? "信頼区間が重なり有意差なし" : diff > 0 ? "より分散" : "より集中"}。`,
    `Diversität ${diff >= 0 ? "+" : ""}${diff.toFixed(4)} gegenüber dem vorherigen Lauf; ${overlap ? "KIs überlappen, kein klarer Unterschied" : diff > 0 ? "diverser" : "konzentrierter"}.`,
  );
}

function showRunStatus(settings) {
  $("status").textContent = P(
    `q=${settings.q} · steps=${settings.steps} · ${settings.repeats} replicas · seed=${settings.seed}`,
    `q=${settings.q} · steps=${settings.steps} · ${settings.repeats} replicas · seed=${settings.seed}`,
    `q=${settings.q} · ステップ=${settings.steps} · ${settings.repeats} 複製 · シード=${settings.seed}`,
    `q=${settings.q} · Schritte=${settings.steps} · ${settings.repeats} Replikate · Seed=${settings.seed}`,
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
    updateInstrumentFromData(result);
    renderDelta();
    if (tracker) {
      tracker.setData({
        shares: result.first.shares[result.first.shares.length - 1],
        steps: result.first.diversity.length,
        peak: result.metrics.peakValue,
        divergence: result.first.finalDiversity,
      });
      $("trackStatus").textContent = P("已锁定", "LOCKED", "ロック済み", "ERFASST");
      $("trackNodes").textContent = "150";
    }
    $("csv").disabled = false;
    $("copy").disabled = false;
    $("compare").disabled = !state.previous;
    $("scrub").disabled = false;
    $("play").disabled = false;
    $("scrub").max = String(result.first.diversity.length - 1);
    $("scrub").value = String(result.first.diversity.length - 1);
    showRunStatus(settings);
    const query = new URLSearchParams({ template: $("template").value, q: settings.q,
      mu: settings.latency_mu, steps: settings.steps, repeats: settings.repeats,
      seed: settings.seed, lang: I18N.lang });
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
    const url = new URL(location.href);
    url.searchParams.set("lang", I18N.lang);
    await navigator.clipboard.writeText(url.toString());
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
if ($("heroRun")) {
  $("heroRun").addEventListener("click", (event) => {
    event.preventDefault();
    const controls = $("controls");
    if (controls) controls.scrollIntoView({ behavior: "smooth", block: "start" });
    if (state.templates.length && !$("run").disabled) $("run").click();
  });
}
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
  if ($("aiRun") && $("aiRun").disabled) $("aiStatus").textContent = T("aiOffline");
  if (state.last) {
    renderSummary(state.last);
    renderMetrics(state.last);
    renderPlain(state.last);
    renderDecision(OpinionSim.decisionBrief(state.config, state.last, $("template").value));
    renderCharts(state.last);
    updateInstrumentFromData(state.last);
    renderDelta();
    $("trackStatus").textContent = P("已锁定", "LOCKED", "ロック済み", "ERFASST");
    if (state.config) showRunStatus(state.config);
  }
});
if ($("langToggle")) {
  $("langToggle").addEventListener("change", (event) => I18N.setLang(event.target.value));
}

if ($("aiRun")) {
  $("aiRun").disabled = true;
  $("aiStatus").textContent = T("aiOffline");
}

boot().catch((error) => { $("error").textContent = error.message; });
