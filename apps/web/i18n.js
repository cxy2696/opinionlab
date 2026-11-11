(function (global) {
  "use strict";
  const STRINGS = {
    title: ["OpinionLab · 情景推演沙盘", "OpinionLab · Scenario Sandbox"],
    bannerStrong: ["先看边界", "BOUNDARY CHECK"],
    bannerText: ["本结果为给定假设下的情景推演，非对真实舆情的预测。",
                 "A scenario simulation under stated assumptions, not a prediction of real opinion."],
    bannerSub: ["仅用于方向性讨论。", "For directional discussion only."],
    heroTitle: ["情景推演沙盘", "Scenario Sandbox"],
    lede: [
      "把一群人会怎么想，变成一套可以反复试、能看到误差范围的追踪系统。",
      "A tracking console for group opinion — reproducible, instrumented, honest about uncertainty.",
    ],
    badgeTracking: ["追踪在线", "TRACKING ONLINE"],
    badgeCi: ["95% 置信区间", "95% CI"],
    badgeAggregate: ["仅群体统计", "AGGREGATE ONLY"],
    trackingLabel: ["实时追踪", "LIVE TRACKING"],
    trackStandby: ["待机", "STANDBY"],
    trackLocked: ["已锁定", "LOCKED"],
    trackNote: ["模拟信号 / 非真实实时数据", "SIMULATED SIGNAL / NOT A REAL-TIME FEED"],
    scenario: ["场景模板", "SCENARIO"],
    knobs: ["调参", "KNOBS"],
    results: ["结果", "RESULTS"],
    qLabel: ["从众强度", "Conformity"],
    qHint: ["为什么调它：判断讨论是自然收敛，还是被从众压力“压”成单一声音。",
            "Why it matters: is the group converging, or being pushed into one voice?"],
    qLow: ["温和", "mild"], qHigh: ["强从众", "strong"],
    latencyLabel: ["平均时延", "Latency"],
    latencyHint: ["反应越慢，窗口越靠后。", "Slower reactions push the window later."],
    stepsLabel: ["观察步数", "Steps"],
    stepsHint: ["看多远；建议覆盖峰值后。", "How far to look; cover the peak."],
    repeatsLabel: ["副本数", "Replicas"],
    repeatsHint: ["越多越稳，但更慢。", "More is steadier, slower."],
    seedLabel: ["随机种子", "Seed"],
    seedHint: ["复现用；换一个看稳健性。", "For reproduction; change it to test robustness."],
    quick: ["快速看", "Quick look"], robust: ["稳健估计", "Steady estimate"],
    highq: ["高从众", "High q"], slow: ["慢反应", "Slow reaction"], reset: ["重置", "Reset"],
    run: ["运行推演", "Run simulation"],
    statusIdle: ["结果在浏览器外计算，可复现。", "Computed outside the browser; reproducible."],
    compare: ["对比上一次", "Compare"], report: ["报告", "Report"],
    csv: ["CSV", "CSV"], copy: ["复制链接", "Copy link"],
    waiting: ["等待运行", "Waiting"],
    summaryIdle: ["选择场景并运行，看看这群人可能怎么走。",
                  "Pick a scenario and run it to see how the group might evolve."],
    decisionTitle: ["决策提示", "Decision brief"],
    decisionTag: ["模拟窗口，不是预测", "SIMULATED WINDOW, NOT A FORECAST"],
    decisionWhat: ["这项推演帮助判断：", "What it informs:"],
    nextTitle: ["建议后续", "Next steps"],
    chartDiversity: ["多样性随时间", "Diversity over time"],
    chartDiversitySub: ["线 = 本次运行 · 带 = 副本 10–90%", "line = this run · band = 10–90%"],
    chartShares: ["观点占比", "Opinion shares"],
    chartCascade: ["每步改变立场的人数", "Cascade per step"],
    replayTitle: ["回放演化", "Replay evolution"],
    replayTag: ["逐帧看占比变化", "Step through the shares"],
    play: ["播放", "Play"],
    metricsTitle: ["指标卡", "Metrics"],
    metricsTag: ["95% CI · n = 副本", "95% CI · n = replicas"],
    guideSummary: ["这些参数到底在做什么？", "Why these knobs"],
    guideQ: ["从众强度 q", "Conformity q"],
    guideQText: ["一个人看到群体里多数是某立场时，跟随的概率有多强。q 越大，群体越容易快速同化；q=1 时接近经典 Voter 模型。",
                 "How strongly a local majority pulls people in. Larger q homogenises faster; q=1 approaches the classical voter model."],
    guideLatency: ["时延 μ", "Latency μ"],
    guideLatencyText: ["反应不是同步的。μ 越大，更新越慢，级联峰值更晚，也更容易出现“拖尾”。",
                       "Reactions are not synchronous. Larger μ delays updates, the cascade peak and the tail."],
    guideSteps: ["步数", "Steps"],
    guideStepsText: ["观察窗口。太短会误判“没收敛”；建议至少覆盖峰值后再多看 30–50 步。",
                     "Observation window. Too short looks like non-convergence; cover the peak and 30–50 steps beyond."],
    guideRepeats: ["副本数", "Replicas"],
    guideRepeatsText: ["同参数独立重复。副本越多，中位数和 CI 越稳；公开演示最多 20，完整产品可到 30+。",
                       "Independent repeats. More replicas tighten the median and CI; the hosted demo caps at 20, the full product supports 30+."],
    guideSeed: ["随机种子", "Seed"],
    guideSeedText: ["固定种子保证同参数可复现；换种子重复，能判断结论是不是“运气好”。",
                    "A fixed seed reproduces a run; changing it shows whether the result was luck."],
    footer: ["只展示群体统计量，不展示任何单节点观点轨迹。",
             "Group-level statistics only; no per-node opinion traces."],
    footerReport: ["报告为单文件离线 HTML", "Report is a single offline HTML file"],
    footerApi: ["API 文档", "API docs"],
    footerLocal: ["在线版为轻量模拟，完整引擎见", "The hosted demo is a lightweight simulation; use the full engine at"],
    fieldTitle: ["3D 观测阵列", "3D telemetry array"],
    fieldWave: ["观点地形", "Opinion terrain"],
    fieldWaveDesc: ["高度 = 多样性；波峰是分歧最大的时刻。", "Height = diversity; peaks are moments of highest disagreement."],
    fieldBars: ["级联柱阵", "Cascade array"],
    fieldBarsDesc: ["柱高 = 该步改变立场的人数比例。", "Column height = share changing stance in that step."],
    fieldCloud: ["立场粒子云", "Stance cloud"],
    fieldCloudDesc: ["颜色比例 = 当前双方占比，旋转观察。", "Color ratio = current stance split; rotates in 3D."],
    fieldWaveLegend: ["点越高 = 分歧越大", "higher dots = more disagreement"],
    fieldBarsLegend: ["悬浮柱体查看步数与比例", "hover a bar for step and share"],
    fieldCloudLegend: ["青 = 立场 0 / 琥珀 = 立场 1", "cyan = stance 0 / amber = stance 1"],
    fieldGuide1: ["① 高度 = 多样性", "① height = diversity"],
    fieldGuide2: ["② 柱高 = 转向比例", "② column = share switching"],
    fieldGuide3: ["③ 颜色 = 立场占比", "③ colour = stance split"],
    fieldGuide4: ["可悬浮读数 · 随回放同步", "hover to read · syncs with replay"],
    fieldAxisTime: ["时间 →", "time →"],
    fieldAxisDiversity: ["多样性 ↑", "diversity ↑"],
    fieldAxisStep: ["步数 →", "step →"],
    fieldAxisShare: ["转向比例 ↑", "share switching ↑"],
    fieldAxisOrbit: ["旋转视角", "orbits in 3D"],
    fieldAxisStance: ["颜色 = 立场", "colour = stance"],
    aiTitle: ["Ollama 辅助推演", "Ollama-assisted explanation"],
    aiTag: ["AI 辅助 · 不是结论", "LLM ASSIST · NOT A CONCLUSION"],
    aiNote: ["用本地 Ollama 把结果翻译成人话，并给出下一步推演建议。它不计算指标、不预测个人，也不是结论。",
             "Use a local Ollama model to restate the numbers and suggest next experiments. It computes no metrics, predicts no individuals and is not a conclusion."],
    aiRun: ["生成辅助解读", "Generate explanation"],
    aiRunning: ["Ollama 正在解读…", "Ollama is thinking…"],
    aiDisabled: ["Ollama 未启用：设置 OLLAMA_ENABLED=true 并运行 ollama serve。",
                 "Ollama is disabled: set OLLAMA_ENABLED=true and run ollama serve."],
    aiOffline: ["在线版不调用本地 Ollama；运行 make demo 并在本地启用。",
                "The hosted demo cannot call local Ollama; run make demo locally with Ollama enabled."],
    aiFailed: ["解读失败，请确认 Ollama 正在运行。", "Explanation failed; check that Ollama is running."],
    readPrefix: ["怎么读：", "How to read:"],
    running: ["运行中…", "running…"],
    runAgain: ["再跑一次", "Run again"],
    ready: ["就绪", "READY"],
  };

  function initial() {
    const fromUrl = new URLSearchParams(location.search).get("lang");
    if (fromUrl === "en" || fromUrl === "zh") return fromUrl;
    const saved = localStorage.getItem("opinionlab-lang");
    if (saved === "en" || saved === "zh") return saved;
    return (navigator.language || "zh").toLowerCase().startsWith("en") ? "en" : "zh";
  }

  const api = {
    lang: initial(),
    strings: STRINGS,
    pick(zh, en) { return api.lang === "en" ? en : zh; },
    t(key) {
      const pair = STRINGS[key];
      if (!pair) return key;
      return api.lang === "en" ? pair[1] : pair[0];
    },
    apply() {
      document.documentElement.lang = api.lang === "en" ? "en" : "zh-CN";
      document.title = api.t("title");
      document.querySelectorAll("[data-i18n]").forEach((el) => {
        el.textContent = api.t(el.dataset.i18n);
      });
      document.querySelectorAll("[data-i18n-html]").forEach((el) => {
        el.innerHTML = api.t(el.dataset.i18nHtml);
      });
      document.querySelectorAll("[data-tip-zh]").forEach((el) => {
        el.dataset.tip = api.lang === "en" ? el.dataset.tipEn : el.dataset.tipZh;
      });
      const toggle = document.getElementById("langToggle");
      if (toggle) toggle.textContent = api.lang === "en" ? "中文" : "EN";
      global.dispatchEvent(new CustomEvent("languagechange", { detail: api.lang }));
    },
    setLang(next) {
      api.lang = next === "en" ? "en" : "zh";
      localStorage.setItem("opinionlab-lang", api.lang);
      const url = new URL(location.href);
      url.searchParams.set("lang", api.lang);
      history.replaceState(null, "", url.toString());
      api.apply();
    },
    toggle() { api.setLang(api.lang === "en" ? "zh" : "en"); },
  };

  global.I18N = api;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => api.apply());
  } else {
    api.apply();
  }
})(typeof window !== "undefined" ? window : globalThis);
