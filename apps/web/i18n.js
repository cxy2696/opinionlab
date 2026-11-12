(function (global) {
  "use strict";
  const STRINGS = {
    title: [
      "OpinionLab · 情景推演沙盘",
      "OpinionLab · Scenario Sandbox",
      "OpinionLab · シナリオ・サンドボックス",
      "OpinionLab · Szenario-Sandbox",
    ],
    bannerStrong: ["先看边界", "BOUNDARY CHECK", "境界条件を確認", "GRENZEN PRÜFEN"],
    bannerText: [
      "本结果为给定假设下的情景推演，非对真实舆情的预测。",
      "A scenario simulation under stated assumptions, not a prediction of real opinion.",
      "本結果は所定の仮定に基づくシナリオ推計であり、実際の世論の予測ではありません。",
      "Eine Szenariosimulation unter den genannten Annahmen, keine Vorhersage der realen öffentlichen Meinung.",
    ],
    bannerSub: ["仅用于方向性讨论。", "For directional discussion only.", "方向性を議論するための参考情報です。", "Nur zur Richtungsdiskussion."],
    heroTitle: ["情景推演沙盘", "Scenario Sandbox", "シナリオ・サンドボックス", "Szenario-Sandbox"],
    lede: [
      "把一群人会怎么想，变成一套可以反复试、能看到误差范围的追踪系统。",
      "A tracking console for group opinion — reproducible, instrumented, honest about uncertainty.",
      "集団の意見がどう動くかを、再現可能で計測可能、不確実性に正直な追跡コンソールに。",
      "Ein Tracking-Konsolenkonzept für Gruppenmeinungen – reproduzierbar, messbar und ehrlich gegenüber Unsicherheit.",
    ],
    badgeTracking: ["追踪在线", "TRACKING ONLINE", "追跡オンライン", "TRACKING ONLINE"],
    badgeCi: ["95% 置信区间", "95% CI", "95% 信頼区間", "95 %-KI"],
    badgeAggregate: ["仅群体统计", "AGGREGATE ONLY", "集団統計のみ", "NUR AGGREGIERT"],
    trackingLabel: ["实时追踪", "LIVE TRACKING", "ライブ追跡", "LIVE-TRACKING"],
    trackStandby: ["待机", "STANDBY", "待機中", "BEREIT"],
    trackLocked: ["已锁定", "LOCKED", "ロック済み", "ERFASST"],
    trackNote: [
      "模拟信号 / 非真实实时数据",
      "SIMULATED SIGNAL / NOT A REAL-TIME FEED",
      "シミュレーション信号 / リアルタイムデータではありません",
      "SIMULIERTES SIGNAL / KEIN ECHTZEIT-FEED",
    ],
    openConsole: ["进入控制台", "OPEN CONTROL DECK", "コンソールを開く", "KONSOLE ÖFFNEN"],
    runShort: ["运行", "RUN", "実行", "START"],
    clusterScenario: ["当前场景", "SCENARIO", "現在のシナリオ", "SZENARIO"],
    gaugeCohesionCaption: ["群体共识度", "group cohesion", "集団の結束度", "Gruppenkohäsion"],
    gaugeTurnCaption: ["单步最大转向", "peak share switching", "最大の立場転換", "Stärkster Meinungswechsel"],
    kpiSteps: ["观测步数", "STEPS OBSERVED", "観測ステップ", "BEOBACHTETE SCHRITTE"],
    kpiMajority: ["副本平均多数", "MEAN MAJORITY", "平均多数到達", "Ø MEHRHEITSSCHRITT"],
    kpiPeak: ["级联峰值", "PEAK TURN", "ピーク転換", "PEAK-WECHSEL"],
    kpiCi: ["95% 置信区间", "95% CONFIDENCE", "95% 信頼区間", "95 %-KONFIDENZ"],
    unitSteps: ["步", "steps", "ステップ", "Schritte"],
    unitCi: ["多样性", "diversity", "多様性", "Diversität"],
    scenario: ["场景模板", "SCENARIO", "シナリオ", "SZENARIO"],
    knobs: ["调参", "KNOBS", "パラメータ", "PARAMETER"],
    results: ["结果", "RESULTS", "結果", "ERGEBNISSE"],
    qLabel: ["从众强度", "Conformity", "同調の強さ", "Konformität"],
    qHint: [
      "为什么调它：判断讨论是自然收敛，还是被从众压力“压”成单一声音。",
      "Why it matters: is the group converging, or being pushed into one voice?",
      "調整の意味：議論が自然に収束しているのか、同調圧力で一つの声に押しつぶされているのかを見極めます。",
      "Warum wichtig: Konvergiert die Gruppe natürlich, oder drückt Konformität sie in eine einzige Stimme?",
    ],
    qLow: ["温和", "mild", "弱い", "mild"],
    qHigh: ["强从众", "strong", "強い同調", "stark"],
    latencyLabel: ["平均时延", "Latency", "平均遅延", "Latenz"],
    latencyHint: ["反应越慢，窗口越靠后。", "Slower reactions push the window later.", "反応が遅いほど、観測ウィンドウは後ろにずれます。", "Langsamere Reaktionen verschieben das Fenster nach hinten."],
    stepsLabel: ["观察步数", "Steps", "観測ステップ", "Schritte"],
    stepsHint: ["看多远；建议覆盖峰值后。", "How far to look; cover the peak.", "どこまで見るか。ピーク後まで含めるのがおすすめです。", "Wie weit beobachten? Den Peak und danach abdecken."],
    repeatsLabel: ["副本数", "Replicas", "複製回数", "Wiederholungen"],
    repeatsHint: ["越多越稳，但更慢。", "More is steadier, slower.", "多いほど安定しますが、時間がかかります。", "Mehr ist stabiler, aber langsamer."],
    seedLabel: ["随机种子", "Seed", "乱数シード", "Zufalls-Seed"],
    seedHint: ["复现用；换一个看稳健性。", "For reproduction; change it to test robustness.", "再現用。変えて堅牢性を確認できます。", "Für Reproduktion; ändern, um Robustheit zu prüfen."],
    quick: ["快速看", "Quick look", "クイック確認", "Schnellblick"],
    robust: ["稳健估计", "Steady estimate", "安定推定", "Stabile Schätzung"],
    highq: ["高从众", "High q", "高同調", "Hohe q"],
    slow: ["慢反应", "Slow reaction", "遅い反応", "Langsame Reaktion"],
    reset: ["重置", "Reset", "リセット", "Zurücksetzen"],
    run: ["运行推演", "Run simulation", "シミュレーション実行", "Simulation starten"],
    statusIdle: [
      "结果在浏览器外计算，可复现。",
      "Computed outside the browser; reproducible.",
      "結果はブラウザ外で計算され、再現可能です。",
      "Berechnung außerhalb des Browsers; reproduzierbar.",
    ],
    compare: ["对比上一次", "Compare", "前回と比較", "Vergleichen"],
    report: ["报告", "Report", "レポート", "Bericht"],
    csv: ["CSV", "CSV", "CSV", "CSV"],
    copy: ["复制链接", "Copy link", "リンクをコピー", "Link kopieren"],
    waiting: ["等待运行", "Waiting", "実行待ち", "Wartend"],
    loadingText: [
      "正在跑副本，收集 95% CI…",
      "Running replicas and collecting 95% CI…",
      "複製を実行して95% CIを集計中…",
      "Replikate laufen; 95 %-KI wird berechnet…",
    ],
    summaryIdle: [
      "选择场景并运行，看看这群人可能怎么走。",
      "Pick a scenario and run it to see how the group might evolve.",
      "シナリオを選んで実行し、集団がどう動くか見てみましょう。",
      "Szenario wählen und ausführen, um die mögliche Entwicklung zu sehen.",
    ],
    decisionTitle: ["决策提示", "Decision brief", "意思決定のヒント", "Entscheidungshinweis"],
    decisionTag: [
      "模拟窗口，不是预测",
      "SIMULATED WINDOW, NOT A FORECAST",
      "シミュレーション上の窓であり予測ではありません",
      "SIMULIERTES FENSTER, KEINE PROGNOSE",
    ],
    decisionWhat: ["这项推演帮助判断：", "What it informs:", "この推計が判断に役立つこと：", "Was diese Auswertung zeigt:"],
    nextTitle: ["建议后续", "Next steps", "次のステップ", "Nächste Schritte"],
    chartDiversity: ["多样性随时间", "Diversity over time", "多様性の推移", "Diversität im Zeitverlauf"],
    chartDiversitySub: [
      "线 = 本次运行 · 带 = 副本 10–90%",
      "line = this run · band = 10–90%",
      "線 = 今回の実行 · 帯 = 複製の10–90%",
      "Linie = dieser Lauf · Band = 10–90 % der Replikate",
    ],
    chartShares: ["观点占比", "Opinion shares", "意見の割合", "Meinungsanteile"],
    chartCascade: ["每步改变立场的人数", "Cascade per step", "各ステップで立場を変えた人数", "Meinungswechsel pro Schritt"],
    replayTitle: ["回放演化", "Replay evolution", "進化のリプレイ", "Verlauf abspielen"],
    replayTag: ["逐帧看占比变化", "Step through the shares", "コマ送りで割合を確認", "Anteile Schritt für Schritt"],
    play: ["播放", "Play", "再生", "Abspielen"],
    metricsTitle: ["指标卡", "Metrics", "指標カード", "Kennzahlen"],
    metricsTag: ["95% CI · n = 副本", "95% CI · n = replicas", "95% CI · n = 複製", "95 %-KI · n = Replikate"],
    guideSummary: ["这些参数到底在做什么？", "Why these knobs", "これらのパラメータは何をしている？", "Was bewirken diese Parameter?"],
    guideQ: ["从众强度 q", "Conformity q", "同調の強さ q", "Konformität q"],
    guideQText: [
      "一个人看到群体里多数是某立场时，跟随的概率有多强。q 越大，群体越容易快速同化；q=1 时接近经典 Voter 模型。",
      "How strongly a local majority pulls people in. Larger q homogenises faster; q=1 approaches the classical voter model.",
      "周囲の多数派に引き寄せられる強さ。q が大きいほど早く同質化し、q=1 は古典的 Voter モデルに近づきます。",
      "Wie stark eine lokale Mehrheit Menschen anzieht. Ein größeres q homogenisiert schneller; q=1 nähert sich dem klassischen Voter-Modell.",
    ],
    guideLatency: ["时延 μ", "Latency μ", "遅延 μ", "Latenz μ"],
    guideLatencyText: [
      "反应不是同步的。μ 越大，更新越慢，级联峰值更晚，也更容易出现“拖尾”。",
      "Reactions are not synchronous. Larger μ delays updates, the cascade peak and the tail.",
      "反応は同期しません。μ が大きいほど更新が遅れ、ピークと裾が後ろに伸びます。",
      "Reaktionen sind nicht synchron. Ein größeres μ verzögert Updates, den Kaskadenpeak und den Ausläufer.",
    ],
    guideSteps: ["步数", "Steps", "ステップ", "Schritte"],
    guideStepsText: [
      "观察窗口。太短会误判“没收敛”；建议至少覆盖峰值后再多看 30–50 步。",
      "Observation window. Too short looks like non-convergence; cover the peak and 30–50 steps beyond.",
      "観測ウィンドウ。短すぎると未収束に見えるため、ピーク後に30–50ステップ以上を見ます。",
      "Beobachtungsfenster. Zu kurz wirkt wie Nicht-Konvergenz; den Peak und 30–50 Schritte danach abdecken.",
    ],
    guideRepeats: ["副本数", "Replicas", "複製回数", "Wiederholungen"],
    guideRepeatsText: [
      "同参数独立重复。副本越多，中位数和 CI 越稳；公开演示最多 20，完整产品可到 30+。",
      "Independent repeats. More replicas tighten the median and CI; the hosted demo caps at 20, the full product supports 30+.",
      "同じ条件での独立試行。複製が多いほど中央値と CI が安定します。公開デモは最大20、完全版は30以上に対応。",
      "Unabhängige Wiederholungen. Mehr Replikate stabilisieren Median und KI; die gehostete Demo ist bei 20 gedeckelt, das Vollprodukt erlaubt 30+.",
    ],
    guideSeed: ["随机种子", "Seed", "乱数シード", "Zufalls-Seed"],
    guideSeedText: [
      "固定种子保证同参数可复现；换种子重复，能判断结论是不是“运气好”。",
      "A fixed seed reproduces a run; changing it shows whether the result was luck.",
      "固定シードで同条件を再現できます。シードを変えて、結果が偶然かどうかを確認します。",
      "Ein fester Seed reproduziert einen Lauf; ein anderer Seed zeigt, ob das Ergebnis Glück war.",
    ],
    footer: [
      "只展示群体统计量，不展示任何单节点观点轨迹。",
      "Group-level statistics only; no per-node opinion traces.",
      "集団レベルの統計のみを表示し、個々のノードの意見推移は表示しません。",
      "Nur Gruppenstatistiken; keine Meinungsverläufe einzelner Knoten.",
    ],
    footerReport: ["报告为单文件离线 HTML", "Report is a single offline HTML file", "レポートは単一のオフラインHTMLです", "Bericht als einzelne Offline-HTML-Datei"],
    footerApi: ["API 文档", "API docs", "APIドキュメント", "API-Doku"],
    footerLocal: [
      "在线版为轻量模拟，完整引擎见",
      "The hosted demo is a lightweight simulation; use the full engine at",
      "オンライン版は軽量シミュレーションです。完全なエンジンは",
      "Die Online-Demo ist eine leichte Simulation; die vollständige Engine unter",
    ],
    fieldTitle: ["3D 观测阵列", "3D telemetry array", "3Dテレメトリ配列", "3D-Telemetrie-Array"],
    fieldWave: ["观点地形", "Opinion terrain", "意見の地形", "Meinungsterrain"],
    fieldWaveDesc: [
      "高度 = 多样性；波峰是分歧最大的时刻。",
      "Height = diversity; peaks are moments of highest disagreement.",
      "高さ = 多様性。山が最も意見が割れた時点です。",
      "Höhe = Diversität; Gipfel sind Momente der stärksten Uneinigkeit.",
    ],
    fieldBars: ["级联柱阵", "Cascade array", "カスケード配列", "Kaskaden-Array"],
    fieldBarsDesc: [
      "柱高 = 该步改变立场的人数比例。",
      "Column height = share changing stance in that step.",
      "柱の高さ = そのステップで立場を変えた人の割合。",
      "Säulenhöhe = Anteil der Personen, die in diesem Schritt die Haltung wechseln.",
    ],
    fieldCloud: ["立场粒子云", "Stance cloud", "立場の粒子クラウド", "Haltungs-Wolke"],
    fieldCloudDesc: [
      "颜色比例 = 当前双方占比，旋转观察。",
      "Color ratio = current stance split; rotates in 3D.",
      "色の比率 = 現在の立場の割合。3Dで回転して確認できます。",
      "Farbverhältnis = aktuelle Haltungsverteilung; rotiert in 3D.",
    ],
    fieldWaveLegend: ["点越高 = 分歧越大", "higher dots = more disagreement", "点が高いほど = 意見が割れている", "höhere Punkte = mehr Uneinigkeit"],
    fieldBarsLegend: ["悬浮柱体查看步数与比例", "hover a bar for step and share", "柱にカーソルを合わせてステップと割合を表示", "Mit der Maus über eine Säule fahren für Schritt und Anteil"],
    fieldCloudLegend: ["青 = 立场 0 / 琥珀 = 立场 1", "cyan = stance 0 / amber = stance 1", "シアン = 立場0 / アンバー = 立場1", "Cyan = Haltung 0 / Amber = Haltung 1"],
    fieldGuide1: ["① 高度 = 多样性", "① height = diversity", "① 高さ = 多様性", "① Höhe = Diversität"],
    fieldGuide2: ["② 柱高 = 转向比例", "② column = share switching", "② 柱の高さ = 転向率", "② Säule = Wechselanteil"],
    fieldGuide3: ["③ 颜色 = 立场占比", "③ colour = stance split", "③ 色 = 立場の割合", "③ Farbe = Haltungsanteil"],
    fieldGuide4: ["可悬浮读数 · 随回放同步", "hover to read · syncs with replay", "ホバーで読取 · リプレイと同期", "Hover zum Lesen · synchron zur Wiedergabe"],
    fieldAxisTime: ["时间 →", "time →", "時間 →", "Zeit →"],
    fieldAxisDiversity: ["多样性 ↑", "diversity ↑", "多様性 ↑", "Diversität ↑"],
    fieldAxisStep: ["步数 →", "step →", "ステップ →", "Schritt →"],
    fieldAxisShare: ["转向比例 ↑", "share switching ↑", "転向率 ↑", "Wechselanteil ↑"],
    fieldAxisOrbit: ["旋转视角", "orbits in 3D", "3Dで回転", "rotiert in 3D"],
    fieldAxisStance: ["颜色 = 立场", "colour = stance", "色 = 立場", "Farbe = Haltung"],
    aiTitle: ["Ollama 辅助推演", "Ollama-assisted explanation", "Ollama 補助解説", "Ollama-gestützte Erklärung"],
    aiTag: ["AI 辅助 · 不是结论", "LLM ASSIST · NOT A CONCLUSION", "AI補助 · 結論ではありません", "KI-ASSISTENZ · KEINE SCHLUSSFOLGERUNG"],
    aiNote: [
      "用本地 Ollama 把结果翻译成人话，并给出下一步推演建议。它不计算指标、不预测个人，也不是结论。",
      "Use a local Ollama model to restate the numbers and suggest next experiments. It computes no metrics, predicts no individuals and is not a conclusion.",
      "ローカルの Ollama で結果を平易に説明し、次の実験を提案します。指標の計算や個人予測は行わず、結論でもありません。",
      "Ein lokales Ollama-Modell formuliert die Zahlen verständlich und schlägt nächste Experimente vor. Es berechnet keine Kennzahlen, sagt keine Personen voraus und ist keine Schlussfolgerung.",
    ],
    aiRun: ["生成辅助解读", "Generate explanation", "補助解説を生成", "Erklärung erzeugen"],
    aiRunning: ["Ollama 正在解读…", "Ollama is thinking…", "Ollama が解説中…", "Ollama denkt nach…"],
    aiDisabled: [
      "Ollama 未启用：设置 OLLAMA_ENABLED=true 并运行 ollama serve。",
      "Ollama is disabled: set OLLAMA_ENABLED=true and run ollama serve.",
      "Ollama は無効です。OLLAMA_ENABLED=true を設定し、ollama serve を実行してください。",
      "Ollama ist deaktiviert: OLLAMA_ENABLED=true setzen und ollama serve starten.",
    ],
    aiOffline: [
      "在线版不调用本地 Ollama；运行 make demo 并在本地启用。",
      "The hosted demo cannot call local Ollama; run make demo locally with Ollama enabled.",
      "オンライン版はローカル Ollama を呼び出せません。ローカルで make demo を実行し、Ollama を有効にしてください。",
      "Die gehostete Demo kann kein lokales Ollama aufrufen; make demo lokal mit aktiviertem Ollama ausführen.",
    ],
    aiFailed: ["解读失败，请确认 Ollama 正在运行。", "Explanation failed; check that Ollama is running.", "解説に失敗しました。Ollama が動作しているか確認してください。", "Erklärung fehlgeschlagen; prüfen, ob Ollama läuft."],
    readPrefix: ["怎么读：", "How to read:", "読み方：", "So lesen:"],
    running: ["运行中…", "running…", "実行中…", "läuft…"],
    runAgain: ["再跑一次", "Run again", "もう一度実行", "Erneut starten"],
    ready: ["就绪", "READY", "準備完了", "BEREIT"],
    controlDeckLabel: ["01 // 控制台", "01 // CONTROL DECK", "01 // コントロールデッキ", "01 // STEUERKONSOLE"],
    telemetryDeckLabel: ["02 // 遥测台", "02 // TELEMETRY DECK", "02 // テレメトリーデッキ", "02 // TELEMETRIE"],
    controlDeckShort: ["控制台", "CONTROL DECK", "コントロールデッキ", "KONSOLE"],
    gaugeCohesion: ["共识度", "COHESION", "結束度", "KOHÄSION"],
    gaugeTurn: ["峰值转向", "PEAK TURN", "ピーク転換", "PEAK-WECHSEL"],
    hudNodes: ["节点", "NODES", "ノード", "KNOTEN"],
    hudStep: ["步", "STEP", "ステップ", "SCHRITT"],
    hudDivergence: ["分歧", "DIVERGENCE", "分岐", "DIVERGENZ"],
    stepLabel: ["步", "step", "ステップ", "Schritt"],
    noMajority: [
      "无副本达到多数",
      "no replica reached a majority",
      "多数に達した複製はありません",
      "Kein Replikat erreichte eine Mehrheit",
    ],
    statusCopied: ["参数链接已复制", "link copied", "パラメータリンクをコピーしました", "Parameterlink kopiert"],
    statusBuildingReport: ["正在生成报告…", "building report…", "レポートを生成中…", "Bericht wird erstellt…"],
    reportFailed: ["报告生成失败", "report failed", "レポートの生成に失敗しました", "Berichtserstellung fehlgeschlagen"],
    aiAssistLabel: ["辅助解读", "assistive narration", "補助解説", "Assistenz-Erzählung"],
  };

  // Japanese and German scenario copy. English and Chinese source text ships
  // with the scenario templates; these fields are merged in at render time.
  const TEMPLATES = {
    G1: {
      name: { ja: "学術再現", de: "Wissenschaftliche Reproduktion" },
      question: {
        ja: "古典的Voter極限（q=1、L=1、二元ハイパーエッジ）では、合意確率は規模とともに予想どおり低下するか？",
        de: "Sinkt im klassischen Voter-Grenzfall (q=1, L=1, binäre Hyperkanten) die Konsenswahrscheinlichkeit erwartungsgemäß mit der Größe?",
      },
      interpretation: {
        ja: "合意確率が n とともに単調に低下することは、実装の正しさを確認する数学的基準になる。",
        de: "Eine mit n fallende Konsenswahrscheinlichkeit dient als mathematischer Korrektheitsanker.",
      },
      decision: { ja: "モデル挙動が古典的極限に一致するか（研究上の判断）", de: "Ob das Modellverhalten dem klassischen Grenzfall entspricht" },
    },
    G2: {
      name: { ja: "ファクトチェック", de: "Faktenprüfung" },
      question: {
        ja: "異なる拡散段階でのファクトチェックは、誤情報の二次拡散を止められるか？",
        de: "Kann Faktenprüfung in verschiedenen Verbreitungsphasen die Sekundärverbreitung von Fehlinformationen stoppen?",
      },
      interpretation: {
        ja: "チェックが早いほどカスケードの裾は短くなる。CIが重なる場合、タイミングは主要因ではない。",
        de: "Frühere Prüfungen verkürzen den Kaskadenschwanz; überlappende KIs bedeuten, dass das Timing nicht der Treiber ist.",
      },
      decision: { ja: "ファクトチェックの介入タイミング", de: "Zeitpunkt der Faktenprüfung" },
    },
    G3: {
      name: { ja: "公衆衛生", de: "Öffentliche Gesundheit" },
      question: {
        ja: "権威ある情報源が集中的に発信すると、感染症の話題で安定した前向きの合意が形成されるか？",
        de: "Kann konzentrierte Kommunikation autoritativer Quellen in einem Ausbruchsthema einen stabilen positiven Konsens bilden?",
      },
      interpretation: {
        ja: "初期の立場の割合が高いほど早く収束するが、過度な集中は多様性を下げる可能性がある。",
        de: "Ein höherer gesetzter Anteil konvergiert schneller, aber Überkonzentration kann die Vielfalt unterdrücken.",
      },
      decision: { ja: "公衆衛生メッセージを集中投入するタイミング", de: "Zeitpunkt konzentrierter Public-Health-Kommunikation" },
    },
    G4: {
      name: { ja: "プラットフォームのシステミックリスク", de: "Systemisches Plattformrisiko" },
      question: {
        ja: "ハイパーエッジが増え続けると、プラットフォームの話題は高変動で収束しにくい状態に入るか？",
        de: "Können Plattformthemen bei wachsenden Hyperkanten in einen hochvolatilen, nicht konvergierenden Zustand geraten?",
      },
      interpretation: {
        ja: "トポロジーの成長と高い同調 q は cascade p99 を大きく上げ、収束を遅らせる。",
        de: "Topologie-Wachstum plus hohe Konformität q erhöht cascade p99 und verzögert die Konvergenz.",
      },
      decision: { ja: "プラットフォームのシステミックリスクを観測する窓", de: "Beobachtungsfenster für systemische Plattformrisiken" },
    },
    G5: {
      name: { ja: "選挙研究テンプレート", de: "Wahlforschungs-Vorlage" },
      question: {
        ja: "選挙周期の中で、意見分布とカスケードは再現可能な周期構造を示すか？",
        de: "Zeigen Meinungsverteilungen und Kaskaden über einen Wahlzyklus eine reproduzierbare zyklische Struktur?",
      },
      interpretation: {
        ja: "このテンプレートは承認された学術研究でのみ使用できます。",
        de: "Diese Vorlage ist nur für genehmigte akademische Forschung verfügbar.",
      },
      decision: { ja: "選挙研究のコンプライアンス境界（承認が必要）", de: "Compliance-Grenzen für Wahlforschung (Genehmigung erforderlich)" },
    },
    G6: {
      name: { ja: "災害警報", de: "Katastrophenwarnung" },
      question: {
        ja: "災害警報の発令後、情報は短時間で大多数のノードに届き、安定するか？",
        de: "Kann eine Katastrophenwarnung nach der Ausgabe schnell die meisten Knoten erreichen und stabil bleiben?",
      },
      interpretation: {
        ja: "警報後に前向きの割合が急速に上がり、その後戻らなければ coverage は有効。そうでなければチャネルを追加する。",
        de: "Ein schneller, nicht zurückgehender Anstieg des positiven Anteils bedeutet, dass die Abdeckung funktioniert hat; sonst Kanäle ergänzen.",
      },
      decision: { ja: "災害警報を発令するタイミング", de: "Zeitpunkt einer Katastrophenwarnung" },
    },
    G7: {
      name: { ja: "企業変革コミュニケーション", de: "Kommunikation bei Unternehmenswandel" },
      question: {
        ja: "組織変革のコミュニケーションのリズムは、従業員の意見の分極と揺り戻しにどう影響するか？",
        de: "Wie beeinflusst der Rhythmus der Kommunikation bei organisatorischen Veränderungen die Polarisierung und das Zurückkehren der Mitarbeitermeinungen?",
      },
      interpretation: {
        ja: "段階的なコミュニケーションは初期の衝撃を和らげるが、間隔が長すぎると否定的な意見が再び集まる。",
        de: "Gestaffelte Kommunikation mildert den ersten Schock, aber lange Pausen lassen negative Meinungen wieder erstarken.",
      },
      decision: { ja: "企業変革コミュニケーションのペース", de: "Takt der Kommunikation bei Unternehmenswandel" },
    },
    S1: {
      name: { ja: "政策発表のペース", de: "Takt der Politikveröffentlichung" },
      question: {
        ja: "政策を段階的に発表すると、世論の議論はどのステップでピークに達し、その後沈静化するか？",
        de: "Bei welchem Schritt erreicht die öffentliche Diskussion ihren Höhepunkt, wenn eine Politik gestaffelt veröffentlicht wird, und flacht sie danach ab?",
      },
      interpretation: {
        ja: "ピーク後に多様性が急速に下がるなら、議論は単一の物語に収束している。介入後もカスケードが高ければ、コミュニケーション期間を延ばす。",
        de: "Ein schneller Diversitätsabfall nach dem Peak bedeutet Konvergenz auf eine einzige Erzählung; hohe Kaskaden nach dem Eingriff sprechen für ein längeres Kommunikationsfenster.",
      },
      decision: { ja: "段階的な政策発表のペースと窓", de: "Takt und Zeitfenster gestaffelter Politikveröffentlichungen" },
    },
    S2: {
      name: { ja: "デマ訂正のタイミング", de: "Timing der Richtigstellung" },
      question: {
        ja: "デマのピーク前と後で訂正情報を出すとき、最終的な否定的意見の割合はどれだけ変わるか？",
        de: "Wie stark unterscheidet sich der endgültige negative Anteil, wenn vor bzw. nach dem Höhepunkt des Gerüchts richtiggestellt wird?",
      },
      interpretation: {
        ja: "早く訂正するほど否定的な割合は下がる。CIが重なる場合、タイミング効果は確認できない。",
        de: "Frühere Richtigstellungen senken den negativen Anteil; überlappende KIs belegen keinen Timing-Effekt.",
      },
      decision: { ja: "訂正情報の投入タイミングと強度", de: "Timing und Stärke von Richtigstellungen" },
    },
    S3: {
      name: { ja: "プラットフォーム統治", de: "Plattform-Governance" },
      question: {
        ja: "プラットフォームのスロットリングや冷却措置は、過激なナラティブのカスケード規模を抑えられるか？",
        de: "Können Drosselung und Deeskalation auf Plattformen die Kaskadengröße extremer Narrative reduzieren?",
      },
      interpretation: {
        ja: "モデレーション後に cascade p99 が下がり収束が速まれば有効。そうでなければ議論が別の場所へ移っただけの可能性がある。",
        de: "Sinkt cascade p99 nach der Moderation und beschleunigt sich die Konvergenz, spricht das für Wirksamkeit; sonst verlagert sich die Diskussion möglicherweise nur.",
      },
      decision: { ja: "プラットフォーム統治の介入タイミング", de: "Zeitpunkt von Plattform-Governance-Eingriffen" },
    },
    S4: {
      name: { ja: "ブランドKOL構成", de: "Marken-KOL-Mix" },
      question: {
        ja: "トップKOLとロングテールクリエイターの構成比は、ブランド話題の意見分布を変えるか？",
        de: "Ändert das Verhältnis von Top-KOLs zu Long-Tail-Creatoren die Meinungsverteilung zu einer Marke?",
      },
      interpretation: {
        ja: "KOLの重みが高いと初期カスケードは大きくなるが後半の多様性は下がる。リーチと多元性のトレードオフ。",
        de: "Höheres KOL-Gewicht erzeugt größere frühe Kaskaden, aber geringere späte Diversität – ein Zielkonflikt zwischen Reichweite und Pluralität.",
      },
      decision: { ja: "ブランドKOLと一般ユーザーの構成とペース", de: "Mix und Takt von KOLs und organischer Reichweite" },
    },
    S5: {
      name: { ja: "緊急科学リテラシー", de: "Wissenschaftskompetenz im Notfall" },
      question: {
        ja: "突発的な公衆衛生事態で、科学コミュニケーションはパニック的な意見の割合を下げられるか？",
        de: "Kann Wissenschaftskommunikation in einem akuten Gesundheitsnotfall den Anteil panikgetriebener Meinungen senken?",
      },
      interpretation: {
        ja: "早い科学コミュニケーションは前向きな割合を高める。遅延が大きい場合は、権威ある情報源による反復的な到達が必要。",
        de: "Frühere Wissenschaftskommunikation erhöht den positiven Anteil; bei langer Latenz sind wiederholte autoritative Kontakte nötig.",
      },
      decision: { ja: "緊急科学コミュニケーションの投入タイミング", de: "Zeitpunkt der Wissenschaftskommunikation im Notfall" },
    },
    S6: {
      name: { ja: "金融期待のコミュニケーション", de: "Kommunikation finanzieller Erwartungen" },
      question: {
        ja: "規制当局のコミュニケーションのペースは、市場センチメントの収束速度とテールリスクにどう影響するか？",
        de: "Wie beeinflusst der Rhythmus der Regulierungskommunikation die Konvergenzgeschwindigkeit der Marktstimmung und das Tail-Risiko?",
      },
      interpretation: {
        ja: "段階的なコミュニケーションは cascade p99 を下げるが、収束時間を延ばす可能性がある。安定性と速度のトレードオフ。",
        de: "Schrittweise Kommunikation senkt cascade p99, kann aber die Konvergenz verlängern; Stabilität gegen Geschwindigkeit.",
      },
      decision: { ja: "金融期待コミュニケーションのペース", de: "Takt der Kommunikation finanzieller Erwartungen" },
    },
    S7: {
      name: { ja: "コミュニティ合意", de: "Konsens in der Community" },
      question: {
        ja: "一度のコミュニティ議論で、穏やかなファシリテーションは少数派を沈黙させずに意見の相違を収束させられるか？",
        de: "Kann eine leichte Moderation eine Community-Diskussion zur Konvergenz bringen, ohne die Minderheit zum Schweigen zu bringen?",
      },
      interpretation: {
        ja: "収束ステップが短くなり、多様性がゼロに崩れなければ、合意形成であり抑圧ではない。",
        de: "Ein kürzerer Konsensschritt ohne Kollaps der Diversität auf null spricht für Konsens statt Unterdrückung.",
      },
      decision: { ja: "コミュニティ議論に軽いファシリテーションが必要か、いつ行うか", de: "Ob und wann eine Community-Diskussion moderiert werden sollte" },
    },
    S8: {
      name: { ja: "組織変革", de: "Organisatorischer Wandel" },
      question: {
        ja: "変革のニュースを段階的に出すとき、従業員感情はどのステップで反発し、コミュニケーションのリズムは対立を減らせるか？",
        de: "Bei welchem Schritt rebelliert die Stimmung, wenn Veränderungsnachrichten gestaffelt veröffentlicht werden, und kann der Rhythmus die Polarisierung senken?",
      },
      interpretation: {
        ja: "減衰と介入の後に cascade P99 が下がり、多様性が中程度に保たれれば、議論の余地が残っている。",
        de: "Sinkt cascade P99 nach Dämpfung und Eingriff bei mittlerer Diversität, bleibt Raum für Diskussion.",
      },
      decision: { ja: "組織変革コミュニケーションのペースと窓", de: "Takt und Zeitfenster der Kommunikation bei organisatorischem Wandel" },
    },
    S9: {
      name: { ja: "新製品ローンチ", de: "Produkteinführung" },
      question: {
        ja: "新製品発表時に、クリエイターと実ユーザーの構成比は、口コミの拡散と長期的な多様性にどう影響するか？",
        de: "Wie beeinflusst das Verhältnis von Creators und echten Nutzern beim Launch die Mundpropaganda und die langfristige Diversität?",
      },
      interpretation: {
        ja: "初期のカスケードが大きくても、長期的な口コミが良いとは限らない。後半の多様性と否定的な割合も見る。",
        de: "Eine große frühe Kaskade bedeutet nicht dauerhafte Mundpropaganda; späte Diversität und negativer Anteil beachten.",
      },
      decision: { ja: "新製品発表の投入ペース", de: "Launch-Takt für ein neues Produkt" },
    },
  };

  const LANGUAGES = ["en", "zh", "ja", "de"];
  const STRING_INDEX = { zh: 0, en: 1, ja: 2, de: 3 };
  const HTML_LANG = { en: "en", zh: "zh-CN", ja: "ja", de: "de" };
  const TIP_FIELD = { zh: "tipZh", en: "tipEn", ja: "tipJa", de: "tipDe" };

  function initial() {
    const fromUrl = new URLSearchParams(location.search).get("lang");
    if (LANGUAGES.includes(fromUrl)) return fromUrl;
    const saved = localStorage.getItem("opinionlab-lang");
    if (LANGUAGES.includes(saved)) return saved;
    return "en";
  }

  const api = {
    lang: initial(),
    languages: LANGUAGES,
    strings: STRINGS,
    templates: TEMPLATES,
    pick(zh, en, ja, de) {
      if (api.lang === "zh") return zh;
      if (api.lang === "ja") return ja ?? en ?? zh;
      if (api.lang === "de") return de ?? en ?? zh;
      return en ?? zh;
    },
    t(key) {
      const values = STRINGS[key];
      if (!values) return key;
      return values[STRING_INDEX[api.lang]] ?? values[1] ?? values[0];
    },
    template(template, field) {
      if (!template) return "";
      const extra = TEMPLATES[template.key]?.[field]?.[api.lang];
      if (extra) return extra;
      if (api.lang === "zh") return template[`${field}_zh`] ?? template[`${field}_en`] ?? "";
      return template[`${field}_en`] ?? "";
    },
    apply() {
      document.documentElement.lang = HTML_LANG[api.lang] || "en";
      document.title = api.t("title");
      document.querySelectorAll("[data-i18n]").forEach((el) => {
        el.textContent = api.t(el.dataset.i18n);
      });
      document.querySelectorAll("[data-i18n-html]").forEach((el) => {
        el.innerHTML = api.t(el.dataset.i18nHtml);
      });
      document.querySelectorAll("[data-tip-zh]").forEach((el) => {
        el.dataset.tip = el.dataset[TIP_FIELD[api.lang]] || el.dataset.tipEn || el.dataset.tipZh || "";
      });
      const toggle = document.getElementById("langToggle");
      if (toggle) {
        if (toggle.tagName === "SELECT") toggle.value = api.lang;
        else toggle.textContent = api.lang === "en" ? "中文" : "EN";
      }
      global.dispatchEvent(new CustomEvent("languagechange", { detail: api.lang }));
    },
    setLang(next) {
      api.lang = LANGUAGES.includes(next) ? next : "en";
      localStorage.setItem("opinionlab-lang", api.lang);
      const url = new URL(location.href);
      url.searchParams.set("lang", api.lang);
      history.replaceState(null, "", url.toString());
      api.apply();
    },
    toggle() {
      const index = LANGUAGES.indexOf(api.lang);
      api.setLang(LANGUAGES[(index + 1) % LANGUAGES.length]);
    },
  };

  global.I18N = api;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => api.apply());
  } else {
    api.apply();
  }
})(typeof window !== "undefined" ? window : globalThis);
