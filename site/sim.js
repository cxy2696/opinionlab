/*
 * Lightweight browser simulator for the hosted demo.
 *
 * Fidelity contract (documented in docs/DEMO.md):
 *   - binary stances (K = 2), uniform node weights, mean aggregation;
 *   - the same conformity map, latency clock and stochastic decision rule as
 *     the Python reference kernel;
 *   - normal / exponential / lognormal / constant integer latency;
 *   - one-shot debunk, seed and flip interventions plus additive boost/dampen.
 *
 * The browser preview does NOT implement multi-stance runs, time-varying
 * topology, engagement weights, shocks or continuous latency; those require
 * the Python engine. The client labels this surface as a preview.
 *
 * The output payload matches the FastAPI demo's `/simulate` shape so the UI
 * never has to branch on which backend produced a run.
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
    const seen = new Set();
    const pool = Array.from({ length: nNodes }, (_, i) => i);
    const top = Math.min(maxSize, nNodes);
    let guard = 0;
    while (edges.length < nEdges) {
      guard += 1;
      if (guard > nEdges * 20) break;
      const size = minSize + Math.floor(rng() * (top - minSize + 1));
      for (let i = 0; i < size; i += 1) {
        const j = i + Math.floor(rng() * (nNodes - i));
        const tmp = pool[i];
        pool[i] = pool[j];
        pool[j] = tmp;
      }
      const edge = pool.slice(0, size).sort((a, b) => a - b);
      const key = edge.join(",");
      if (seen.has(key)) continue;
      seen.add(key);
      edges.push(edge);
    }
    return edges;
  }

  function drawLatencies(n, params, rng) {
    const mean = Number(params.latency_mu || 1);
    const sigma = Number(params.latency_sigma || 1);
    const dist = params.latency_dist || "normal";
    const values = new Float64Array(n);
    for (let i = 0; i < n; i += 1) {
      let value;
      if (dist === "const") value = mean;
      else if (dist === "exponential") value = -mean * Math.log(1 - rng());
      else if (dist === "lognormal") value = Math.exp(mean + sigma * gaussian(rng));
      else value = mean + sigma * gaussian(rng);
      values[i] = Math.max(0, Math.round(value));
    }
    return values;
  }

  function initialOpinions(n, params, rng) {
    const opinions = new Uint8Array(n);
    if (params.init_mode === "fixed_ratio") {
      const ones = Math.round(Math.min(1, Math.max(0, Number(params.target_share_1 ?? 0.5))) * n);
      const order = Array.from({ length: n }, (_, i) => i);
      for (let i = 0; i < ones; i += 1) {
        const j = i + Math.floor(rng() * (n - i));
        const tmp = order[i];
        order[i] = order[j];
        order[j] = tmp;
      }
      for (let i = 0; i < ones; i += 1) opinions[order[i]] = 1;
      return opinions;
    }
    for (let i = 0; i < n; i += 1) opinions[i] = rng() < 0.5 ? 1 : 0;
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
    const magnitude = Number(intervention.magnitude || 0);
    if (intervention.type === "boost") return magnitude;
    if (intervention.type === "dampen") return -magnitude;
    if (intervention.type === "weight_shift") return magnitude * 0.5;
    return 0;
  }

  function applyOneShot(intervention, opinions, step, rng) {
    if (!intervention || Number(intervention.at_step) !== step) return;
    const magnitude = Number(intervention.magnitude || 0);
    const count = Math.round(magnitude * opinions.length);
    if (!count) return;
    const indexes = Array.from({ length: opinions.length }, (_, i) => i);
    for (let i = 0; i < count; i += 1) {
      const j = i + Math.floor(rng() * (opinions.length - i));
      const tmp = indexes[i];
      indexes[i] = indexes[j];
      indexes[j] = tmp;
    }
    for (let i = 0; i < count; i += 1) {
      const node = indexes[i];
      if (intervention.type === "debunk") {
        if (opinions[node] === 0) opinions[node] = 1;
      } else if (intervention.type === "seed_opinion") {
        const target = Number((intervention.target && intervention.target.opinion) || 1);
        opinions[node] = target ? 1 : 0;
      } else if (intervention.type === "flip_share") {
        opinions[node] = opinions[node] ? 0 : 1;
      }
    }
  }

  function conformity(ones, zeros, q) {
    if (ones <= 0) return 0;
    if (zeros <= 0) return 1;
    const a = Math.pow(ones, q);
    const b = Math.pow(zeros, q);
    return a / (a + b);
  }

  function runOnce(params) {
    const n = params.n_nodes;
    const m = params.n_edges;
    const q = Number(params.q);
    const steps = params.steps;
    const rng = mulberry32(params.seed);
    const edges = sampleEdges(n, m, params.min_size || 2, params.max_size || 5, rng);
    const incident = Array.from({ length: n }, () => []);
    edges.forEach((edge, index) => edge.forEach((node) => incident[node].push(index)));
    const latencies = drawLatencies(n, params, rng);
    const opinions = initialOpinions(n, params, rng);
    const lastChange = new Int32Array(n);
    const shareSeries = [sharesOf(opinions)];
    let maxShare = Math.max(...shareSeries[0]);
    const diversity = [1 - maxShare];
    const cascade = [];
    let timeToConsensus = maxShare >= 0.8 ? 0 : -1;

    for (let step = 1; step <= steps; step += 1) {
      const before = opinions.slice();
      applyOneShot(params.intervention, opinions, step, rng);
      const bias = biasFor(params.intervention, step);
      const sums = new Float64Array(n);
      const counts = new Float64Array(n);
      edges.forEach((edge) => {
        let ones = 0;
        edge.forEach((node) => { ones += opinions[node]; });
        const zeros = edge.length - ones;
        let p1 = conformity(ones, zeros, q);
        if (bias) p1 = Math.max(0, Math.min(1, p1 + bias));
        edge.forEach((node) => { sums[node] += p1; counts[node] += 1; });
      });
      const next = opinions.slice();
      for (let node = 0; node < n; node += 1) {
        if (!counts[node]) continue;
        if (step - lastChange[node] < latencies[node]) continue;
        next[node] = rng() < sums[node] / counts[node] ? 1 : 0;
      }
      let changedCount = 0;
      for (let node = 0; node < n; node += 1) {
        if (next[node] !== before[node]) {
          lastChange[node] = step;
          changedCount += 1;
        }
      }
      opinions.set(next);
      const shares = sharesOf(opinions);
      shareSeries.push(shares);
      maxShare = Math.max(...shares);
      diversity.push(1 - maxShare);
      cascade.push(changedCount / n);
      if (timeToConsensus < 0 && maxShare >= 0.8) timeToConsensus = step;
    }

    // Mirror `metrics.consensus_stability`: consensus must hold for the
    // longest latency window after it is first reached.
    const window = Math.ceil(Math.max(...latencies));
    const stable = timeToConsensus >= 0
      && timeToConsensus + 1 + window <= shareSeries.length
      && shareSeries
        .slice(timeToConsensus, timeToConsensus + 1 + window)
        .every((share) => Math.max(...share) >= 0.8);

    const finalShares = shareSeries[shareSeries.length - 1];
    const entropy = finalShares.reduce((acc, p) => (p > 0 ? acc - p * Math.log2(p) : acc), 0);
    const rawPolarization = 1 - finalShares.reduce((acc, p) => acc + p * p, 0);
    const polarizationMax = 1 - 1 / finalShares.length;
    return {
      diversity,
      shares: shareSeries,
      cascade,
      timeToConsensus,
      absorbing: stable,
      finalDiversity: diversity[diversity.length - 1],
      finalShares,
      entropy,
      polarization: polarizationMax > 0 ? rawPolarization / polarizationMax : 0,
    };
  }

  // Two-sided 95% Student-t critical values; the normal value is used once the
  // table runs out (df >= 30). Same rule as the Python estimator.
  function tCritical(df) {
    const table = {
      1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
      7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
      13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101,
      19: 2.093, 20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064,
      25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
    };
    return table[df] || 1.96;
  }

  function percentile(values, p) {
    const sorted = values.slice().sort((a, b) => a - b);
    if (!sorted.length) return 0;
    const index = (sorted.length - 1) * p;
    const low = Math.floor(index);
    const high = Math.ceil(index);
    return sorted[low] + (sorted[high] - sorted[low]) * (index - low);
  }

  function mean(values) {
    return values.reduce((a, b) => a + b, 0) / Math.max(1, values.length);
  }

  function interval(values) {
    if (!values.length) return { mean: null, ci95_lo: null, ci95_hi: null, n: 0 };
    const mu = mean(values);
    if (values.length < 2) return { mean: mu, ci95_lo: mu, ci95_hi: mu, n: 1 };
    const variance = values.reduce((acc, value) => acc + (value - mu) ** 2, 0) / (values.length - 1);
    const half = tCritical(values.length - 1) * Math.sqrt(variance / values.length);
    return { mean: mu, ci95_lo: mu - half, ci95_hi: mu + half, n: values.length };
  }

  function runMany(params, repeats) {
    const count = Math.max(1, Number(repeats || params.repeats || 1));
    const runs = [];
    for (let i = 0; i < count; i += 1) {
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
    const reached = runs.map((run) => run.timeToConsensus).filter((value) => value >= 0);
    const metrics = {
      diversity_final: interval(runs.map((run) => run.finalDiversity)),
      cascade_p99: interval(runs.map((run) => percentile(run.cascade, 0.99))),
      time_to_consensus: interval(reached),
      absorbing: interval(runs.map((run) => (run.absorbing ? 1 : 0))),
      entropy_final: interval(runs.map((run) => run.entropy)),
      polarization_final: interval(runs.map((run) => run.polarization)),
    };
    metrics.cascade_max = interval(runs.map((run) => Math.max(0, ...run.cascade)));
    return { runs, first, bands, metrics, reached, count };
  }

  function decisionBrief(params, result, template) {
    const cascade = result.first.cascade;
    const meanCascade = mean(cascade);
    const threshold = Math.max(0.02, meanCascade * 2);
    const takeoffIndex = cascade.findIndex((value) => value >= threshold);
    const peakIndex = cascade.reduce((best, value, index) => (value > cascade[best] ? index : best), 0);
    const peakStep = peakIndex + 1;
    const intervention = params.intervention || null;
    const consensus = result.first.timeToConsensus >= 0 ? result.first.timeToConsensus : null;
    const lead = Math.max(2, Math.round(2 * Number(params.latency_mu || 1)));
    let windowZh;
    let windowEn;
    if (intervention) {
      const start = Math.max(1, peakStep - lead);
      windowZh = `建议把干预放在第 ${start}–${peakStep} 步：峰值前约 ${lead} 步（约两个反应周期）。本次配置在第 ${intervention.at_step} 步。`;
      windowEn = `A simulated window is steps ${start}–${peakStep}: about ${lead} steps before the cascade peak (roughly two reaction cycles). This run intervenes at step ${intervention.at_step}.`;
    } else {
      const start = takeoffIndex >= 0 ? takeoffIndex + 1 : Math.max(1, peakStep - lead);
      windowZh = `重点观察第 ${start}–${peakStep} 步：级联约在第 ${start} 步起势，第 ${peakStep} 步达到峰值。`;
      windowEn = `Watch steps ${start}–${peakStep}: the cascade takes off around step ${start} and peaks at step ${peakStep}.`;
    }
    if (consensus !== null) {
      windowZh += `约第 ${consensus} 步达到多数。`;
      windowEn += ` A majority is reached around step ${consensus}.`;
    }
    const absorbing = result.metrics.absorbing.mean >= 0.5;
    const followupsZh = [
      "把本次参数当作基线，只改一个时点重跑；只有两次的 95% CI 不重叠，才谈“时点有效”。",
      `把副本数加到 30 以上再确认结论；当前副本数为 ${result.count}，区间可能偏宽。`,
      "用真实数据校准 q、时延与初始态度分布；这里的时点是模拟窗口，不是事件预测。",
    ];
    const followupsEn = [
      "Treat this run as the baseline, change only the timing, and rerun; call it effective only when the 95% CIs do not overlap.",
      `Raise replicas to 30+ before relying on the result (currently ${result.count}); the interval may be wide.`,
      "Calibrate q, latency and initial stances on real data; this window is simulated, not an event forecast.",
    ];
    if (absorbing && consensus !== null) {
      followupsZh.push("如果目标是推迟共识，尝试增大时延或降低 q，看窗口是否随之后移。");
      followupsEn.push("If the goal is to delay consensus, try longer latency or lower q and see whether the window moves later.");
    }
    return {
      decision_zh: template.decision_zh || "沟通/干预的时点与力度",
      decision_en: template.decision_en || "when and how strongly to communicate or intervene",
      timing: {
        takeoff_step: takeoffIndex >= 0 ? takeoffIndex + 1 : null,
        peak_step: peakStep,
        consensus_step: consensus,
        intervention_step: intervention ? Number(intervention.at_step) : null,
      },
      window_zh: windowZh,
      window_en: windowEn,
      followups_zh: followupsZh,
      followups_en: followupsEn,
      caveat_zh: "时点建议来自给定假设下的模拟，不构成对真实事件时间的预测。",
      caveat_en: "Timing advice comes from a simulation under stated assumptions and is not a forecast of real event timing.",
    };
  }

  function payload(params, result, template) {
    const first = result.first;
    const metrics = result.metrics;
    const absorbingRate = metrics.absorbing.mean || 0;
    const ttc = first.timeToConsensus >= 0 ? first.timeToConsensus : null;
    const start = first.diversity[0];
    const end = first.diversity[first.diversity.length - 1];
    const peak = first.cascade.length ? Math.max(...first.cascade) : 0;
    const peakStep = first.cascade.length ? first.cascade.indexOf(peak) + 1 : 0;
    const verdictZh = absorbingRate >= 0.5
      ? "形成稳定共识"
      : ttc !== null ? "达到多数，但仍在变化" : "尚未收敛";
    const verdictEn = absorbingRate >= 0.5
      ? "Stable consensus"
      : ttc !== null ? "Majority reached, still moving" : "Not converged";
    const textZh = ttc !== null
      ? `在这组假设下，多样性从 ${start.toFixed(2)} 变到 ${end.toFixed(2)}；约在第 ${ttc} 步达到多数。级联峰值在第 ${peakStep} 步，约 ${(peak * 100).toFixed(0)}% 的人同时改变立场。`
      : `在这组假设下，多样性从 ${start.toFixed(2)} 变到 ${end.toFixed(2)}，但在 ${params.steps} 步内没有达到多数。级联峰值在第 ${peakStep} 步（${(peak * 100).toFixed(0)}%）。`;
    const textEn = ttc !== null
      ? `Under these assumptions diversity moved from ${start.toFixed(2)} to ${end.toFixed(2)}, reaching a majority around step ${ttc}. The cascade peaked at step ${peakStep}, with about ${(peak * 100).toFixed(0)}% changing at once.`
      : `Under these assumptions diversity moved from ${start.toFixed(2)} to ${end.toFixed(2)} without a majority in ${params.steps} steps. The cascade peaked at step ${peakStep} (${(peak * 100).toFixed(0)}%).`;
    const warnings = {};
    const censored = result.runs.filter((run) => run.timeToConsensus < 0).length;
    return {
      template: {
        key: template.key,
        name_zh: template.name_zh,
        name_en: template.name_en,
        question_zh: template.question_zh,
        question_en: template.question_en,
        data_shape_zh: template.data_shape_zh,
        data_shape_en: template.data_shape_en,
        interpretation_zh: template.interpretation_zh,
        interpretation_en: template.interpretation_en,
        assumptions_zh: template.assumptions_zh,
        assumptions_en: template.assumptions_en,
        limitations_zh: template.limitations_zh,
        limitations_en: template.limitations_en,
        decision_zh: template.decision_zh,
        decision_en: template.decision_en,
        real_world_zh: template.real_world_zh,
        real_world_en: template.real_world_en,
        parameters_zh: template.parameters_zh,
        parameters_en: template.parameters_en,
        watch_zh: template.watch_zh,
        watch_en: template.watch_en,
      },
      spec: {
        q: Number(params.q),
        n_steps: Number(params.steps),
        steps: Number(params.steps),
        repeats: result.count,
        seed: Number(params.seed),
        engine: "browser-binary",
        latency_mu: Number(params.latency_mu),
        latency_sigma: Number(params.latency_sigma),
        latency_dist: params.latency_dist,
        n_opinions: 2,
        consensus_threshold: 0.8,
      },
      metrics,
      summary: {
        absorbing: absorbingRate >= 0.5,
        diversity_final: end,
      },
      series: {
        steps: first.diversity.map((_, index) => index),
        diversity: first.diversity,
        cascade: [0].concat(first.cascade),
        shares: first.shares,
        bands: result.bands,
      },
      summary_text: { verdict_zh: verdictZh, verdict_en: verdictEn, text_zh: textZh, text_en: textEn },
      decision: decisionBrief(params, result, template),
      quality: {
        engine: "browser-binary",
        graph: { n_nodes: params.n_nodes, n_edges: params.n_edges, n_opinions: 2 },
        replicas: result.count,
        censored_replicas: censored,
        censored_rate: censored / result.count,
        insufficient_samples: result.count < 30,
        degraded_to_streaming: false,
        warnings,
      },
      opinion_count: 2,
      disclaimer_key: "simulation_not_prediction",
    };
  }

  const api = { runOnce, runMany, payload, decisionBrief, sharesOf, conformity };

  if (typeof module !== "undefined" && module.exports) module.exports = api;
  global.OpinionSim = api;

  if (typeof process !== "undefined" && process.argv[1] && process.argv[1].endsWith("sim.js") && process.argv.includes("--selftest")) {
    const template = { key: "T", decision_zh: "时点", decision_en: "timing" };
    const params = {
      n_nodes: 40, n_edges: 100, q: 1.5, latency_mu: 2, latency_sigma: 1,
      latency_dist: "normal", steps: 20, repeats: 3, min_size: 2, max_size: 5,
      seed: 7, init_mode: "balanced_random", target_share_1: 0.5,
    };
    const a = runOnce(params);
    const b = runOnce(params);
    const ok = a.diversity.length === 21
      && a.shares.every((row) => Math.abs(row[0] + row[1] - 1) < 1e-9)
      && JSON.stringify(a.diversity) === JSON.stringify(b.diversity)
      && a.cascade.length === 20;
    if (!ok) { console.error("selftest failed"); process.exit(1); }
    const many = runMany(params, params.repeats);
    const data = payload(params, many, template);
    if (!Number.isFinite(data.metrics.diversity_final.mean)) { console.error("metrics failed"); process.exit(1); }
    if (data.series.steps.length !== data.series.diversity.length || data.series.cascade.length !== data.series.steps.length) {
      console.error("series length mismatch");
      process.exit(1);
    }
    const fixed = runOnce(Object.assign({}, params, { init_mode: "fixed_ratio", target_share_1: 0.25 }));
    if (fixed.shares[0][1] !== 0.25) { console.error("fixed_ratio failed"); process.exit(1); }
    console.log("sim selftest ok");
  }
})(typeof window !== "undefined" ? window : globalThis);
