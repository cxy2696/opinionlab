/* Lightweight browser demo of the OpinionLab model.
 * Mirrors the binary, uniform-weight, mean-aggregation update: the full engine
 * (multi-opinion, shocks, API, reports) lives in packages/hnle.
 */
(function (global) {
  "use strict";

  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function gaussian(rng) {
    let u = 0;
    let v = 0;
    while (u === 0) u = rng();
    while (v === 0) v = rng();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }

  function sampleEdges(nNodes, nEdges, minSize, maxSize, rng) {
    const edges = [];
    const pool = Array.from({ length: nNodes }, (_, i) => i);
    for (let e = 0; e < nEdges; e += 1) {
      const top = Math.min(maxSize, nNodes);
      const size = minSize + Math.floor(rng() * (top - minSize + 1));
      for (let i = 0; i < size; i += 1) {
        const j = i + Math.floor(rng() * (nNodes - i));
        const tmp = pool[i];
        pool[i] = pool[j];
        pool[j] = tmp;
      }
      edges.push(pool.slice(0, size).sort((a, b) => a - b));
    }
    return edges;
  }

  function initialOpinions(nNodes, rng, intervention) {
    const opinions = new Uint8Array(nNodes);
    for (let i = 0; i < nNodes; i += 1) opinions[i] = rng() < 0.5 ? 1 : 0;
    return opinions;
  }

  function sharesOf(opinions) {
    let ones = 0;
    for (let i = 0; i < opinions.length; i += 1) ones += opinions[i];
    return [1 - ones / opinions.length, ones / opinions.length];
  }

  function biasFor(intervention, step) {
    if (!intervention) return 0;
    const start = Number(intervention.at_step);
    const duration = Number(intervention.duration || 1);
    if (step < start || step >= start + duration) return 0;
    if (intervention.type === "boost") return Number(intervention.magnitude || 0);
    if (intervention.type === "dampen") return -Number(intervention.magnitude || 0);
    return 0;
  }

  function applyOneShot(intervention, opinions, step, rng) {
    if (!intervention || Number(intervention.at_step) !== step) return false;
    const magnitude = Number(intervention.magnitude || 0);
    const count = Math.round(magnitude * opinions.length);
    if (!count) return false;
    const indexes = Array.from({ length: opinions.length }, (_, i) => i);
    for (let i = 0; i < count; i += 1) {
      const j = i + Math.floor(rng() * (opinions.length - i));
      const tmp = indexes[i];
      indexes[i] = indexes[j];
      indexes[j] = tmp;
    }
    let changed = false;
    for (let i = 0; i < count; i += 1) {
      const node = indexes[i];
      if (intervention.type === "debunk") {
        if (opinions[node] === 0) { opinions[node] = 1; changed = true; }
      } else if (intervention.type === "seed_opinion") {
        const target = Number((intervention.target && intervention.target.opinion) || 1);
        if (opinions[node] !== target) { opinions[node] = target; changed = true; }
      } else if (intervention.type === "flip_share") {
        opinions[node] = opinions[node] ? 0 : 1;
        changed = true;
      }
    }
    return changed;
  }

  function runOnce(params) {
    const n = params.n_nodes;
    const m = params.n_edges;
    const q = params.q;
    const steps = params.steps;
    const rng = mulberry32(params.seed);
    const edges = sampleEdges(n, m, params.min_size || 2, params.max_size || 5, rng);
    const incident = Array.from({ length: n }, () => []);
    edges.forEach((edge, index) => edge.forEach((node) => incident[node].push(index)));
    const latencies = new Float64Array(n);
    for (let i = 0; i < n; i += 1) {
      latencies[i] = Math.max(0, Math.round(params.latency_mu + (params.latency_sigma || 1) * gaussian(rng)));
    }
    const opinions = initialOpinions(n, rng, params.intervention);
    const lastChange = new Int32Array(n);
    const diversity = [1 - Math.max(...sharesOf(opinions))];
    const shareSeries = [sharesOf(opinions)];
    const cascade = [];
    let timeToConsensus = -1;

    for (let step = 1; step <= steps; step += 1) {
      const oneShot = applyOneShot(params.intervention, opinions, step, rng);
      const bias = biasFor(params.intervention, step);
      const sums = new Float64Array(n);
      const counts = new Float64Array(n);
      edges.forEach((edge) => {
        let ones = 0;
        edge.forEach((node) => { ones += opinions[node]; });
        const zeros = edge.length - ones;
        let p1 = 0.5;
        if (ones === 0) p1 = 0;
        else if (zeros === 0) p1 = 1;
        else p1 = Math.pow(ones, q) / (Math.pow(ones, q) + Math.pow(zeros, q));
        if (bias) p1 = Math.max(0, Math.min(1, p1 + bias));
        edge.forEach((node) => { sums[node] += p1; counts[node] += 1; });
      });
      const before = opinions.slice();
      const next = opinions.slice();
      for (let node = 0; node < n; node += 1) {
        if (!counts[node]) continue;
        if (step - lastChange[node] < latencies[node]) continue;
        const p1 = sums[node] / counts[node];
        next[node] = rng() < p1 ? 1 : 0;
      }
      let changed = oneShot;
      for (let node = 0; node < n; node += 1) {
        if (next[node] !== before[node]) { lastChange[node] = step; changed = true; }
      }
      opinions.set(next);
      const shares = sharesOf(opinions);
      shareSeries.push(shares);
      diversity.push(1 - Math.max(...shares));
      let changedCount = 0;
      for (let node = 0; node < n; node += 1) if (next[node] !== before[node]) changedCount += 1;
      cascade.push(changedCount / n);
      if (timeToConsensus < 0 && Math.max(...shares) >= 0.8) timeToConsensus = step;
    }
    return {
      steps: diversity.length,
      diversity,
      shares: shareSeries,
      cascade,
      timeToConsensus,
      absorbing: timeToConsensus >= 0,
      finalDiversity: diversity[diversity.length - 1],
      finalShares: shareSeries[shareSeries.length - 1],
    };
  }

  function percentile(values, p) {
    const sorted = values.slice().sort((a, b) => a - b);
    if (!sorted.length) return 0;
    const index = (sorted.length - 1) * p;
    const low = Math.floor(index);
    const high = Math.ceil(index);
    return sorted[low] + (sorted[high] - sorted[low]) * (index - low);
  }

  function runMany(params, repeats) {
    const runs = [];
    for (let i = 0; i < repeats; i += 1) {
      runs.push(runOnce(Object.assign({}, params, { seed: params.seed + i * 1009 })));
    }
    const first = runs[0];
    const bands = { p10: [], p50: [], p90: [] };
    for (let step = 0; step < first.diversity.length; step += 1) {
      const values = runs.map((run) => run.diversity[step]);
      bands.p10.push(percentile(values, 0.1));
      bands.p50.push(percentile(values, 0.5));
      bands.p90.push(percentile(values, 0.9));
    }
    const finalDiversity = runs.map((run) => run.finalDiversity);
    const ttc = runs.map((run) => run.timeToConsensus).filter((value) => value >= 0);
    const mean = (values) => values.reduce((a, b) => a + b, 0) / values.length;
    const ci = (values) => {
      if (values.length < 2) return [mean(values), mean(values)];
      const mu = mean(values);
      const sd = Math.sqrt(values.reduce((acc, value) => acc + (value - mu) ** 2, 0) / (values.length - 1));
      const half = 1.96 * sd / Math.sqrt(values.length);
      return [mu - half, mu + half];
    };
    const diversityMean = mean(finalDiversity);
    const diversityCi = ci(finalDiversity);
    const peakIndex = first.cascade.reduce((best, value, index) => (value > first.cascade[best] ? index : best), 0);
    return {
      runs,
      first,
      bands,
      metrics: {
        diversity: { mean: diversityMean, lo: diversityCi[0], hi: diversityCi[1], n: repeats },
        consensus: ttc.length ? { mean: mean(ttc), n: ttc.length } : null,
        absorbing: { rate: runs.filter((run) => run.absorbing).length / repeats },
        peakStep: peakIndex + 1,
        peakValue: first.cascade[peakIndex] || 0,
      },
    };
  }

  function decisionBrief(params, result) {
    const cascade = result.first.cascade;
    const meanCascade = cascade.reduce((a, b) => a + b, 0) / Math.max(1, cascade.length);
    const threshold = Math.max(0.02, meanCascade * 2);
    const takeoffIndex = cascade.findIndex((value) => value >= threshold);
    const peakStep = result.metrics.peakStep;
    const intervention = params.intervention || null;
    const consensus = result.first.timeToConsensus >= 0 ? result.first.timeToConsensus : null;
    let windowZh;
    let windowEn;
    if (intervention) {
      const lead = Math.max(2, Math.round(2 * params.latency_mu));
      const start = Math.max(1, peakStep - lead);
      windowZh = `建议把干预放在第 ${start}–${peakStep} 步：峰值前约 ${lead} 步（约两个反应周期）。本次配置在第 ${intervention.at_step} 步。`;
      windowEn = `A simulated window is steps ${start}–${peakStep}: about ${lead} steps before the cascade peak (roughly two reaction cycles). This run intervenes at step ${intervention.at_step}.`;
    } else {
      const start = takeoffIndex >= 0 ? takeoffIndex + 1 : Math.max(1, peakStep - 3);
      windowZh = `重点观察第 ${start}–${peakStep} 步：级联约在第 ${start} 步起势，第 ${peakStep} 步达到峰值。`;
      windowEn = `Watch steps ${start}–${peakStep}: the cascade takes off around step ${start} and peaks at step ${peakStep}.`;
    }
    if (consensus) {
      windowZh += `约第 ${consensus} 步达到多数。`;
      windowEn += ` A majority is reached around step ${consensus}.`;
    }
    const followupsZh = [
      "把本次参数当作基线，只改一个时点重跑；只有两次的 95% CI 不重叠，才谈“时点有效”。",
      "把副本数加到 30 以上再确认结论；当前副本数偏少时区间会很宽。",
      "用真实数据校准 q、时延与初始态度分布；这里的时点是模拟窗口，不是事件预测。",
    ];
    const followupsEn = [
      "Treat this run as the baseline, change only the timing, and rerun; call it effective only when the 95% CIs do not overlap.",
      "Raise replicas to 30+ before relying on the result; small samples give wide intervals.",
      "Calibrate q, latency and initial stances on real data; this window is simulated, not an event forecast.",
    ];
    return {
      decisionZh: result.metrics.absorbing.rate >= 0.5 ? "评估干预时点与沟通节奏" : "评估沟通窗口与观察重点",
      decisionEn: result.metrics.absorbing.rate >= 0.5 ? "assessing intervention timing and cadence" : "assessing the communication window",
      timing: {
        takeoff: takeoffIndex >= 0 ? takeoffIndex + 1 : null,
        peak: peakStep,
        consensus,
        intervention: intervention ? intervention.at_step : null,
      },
      windowZh,
      windowEn,
      followupsZh,
      followupsEn,
      caveatZh: "时点建议来自给定假设下的模拟，不构成对真实事件时间的预测。",
      caveatEn: "Timing advice comes from a simulation under stated assumptions and is not a forecast of real event timing.",
    };
  }

  const api = { runOnce, runMany, decisionBrief, sharesOf };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  global.OpinionSim = api;

  if (typeof process !== "undefined" && process.argv[1] && process.argv[1].endsWith("sim.js") && process.argv.includes("--selftest")) {
    const params = { n_nodes: 40, n_edges: 100, q: 1.5, latency_mu: 2, latency_sigma: 1, steps: 20, repeats: 3, min_size: 2, max_size: 5, seed: 7 };
    const a = runOnce(params);
    const b = runOnce(params);
    const ok = a.diversity.length === 21 && a.shares.every((row) => Math.abs(row[0] + row[1] - 1) < 1e-9) && JSON.stringify(a.diversity) === JSON.stringify(b.diversity);
    if (!ok) { console.error("selftest failed"); process.exit(1); }
    const many = runMany(params, params.repeats);
    if (!Number.isFinite(many.metrics.diversity.mean)) { console.error("metrics failed"); process.exit(1); }
    console.log("sim selftest ok");
  }
})(typeof window !== "undefined" ? window : globalThis);
