/* Industrial 3D tracker: a dependency-free projected hypergraph.
 * It is decorative telemetry for the demo, not a data-accurate renderer.
 */
(function (global) {
  "use strict";
  const TAU = Math.PI * 2;
  const reduceMotion = global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function project(point, rotation, cx, cy, radius) {
    const cos = Math.cos(rotation);
    const sin = Math.sin(rotation);
    const x = point.x * cos - point.z * sin;
    const z = point.x * sin + point.z * cos;
    const tilt = Math.cos(0.35);
    const tiltSin = Math.sin(0.35);
    const y = point.y * tilt - z * tiltSin;
    const depth = point.y * tiltSin + z * tilt + 2.6;
    const scale = Math.min(2.2, 2.0 / Math.max(0.6, depth));
    return { x: cx + x * radius * scale, y: cy + y * radius * scale, depth, scale };
  }

  class Tracker {
    constructor(canvas, options = {}) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.onTick = options.onTick || (() => {});
      this.count = options.count || 150;
      this.nodes = [];
      this.edges = [];
      this.pulses = [];
      this.rotation = 0.6;
      this.step = 0;
      this.share = 0.5;
      this.activity = 0;
      this.active = false;
      this.last = 0;
      this.lastTick = 0;
      this.target = 0;
      this.nextTarget = 0;
      this.timer = 0;
      this.build();
      this.resize();
      this.bind();
      if (!reduceMotion) requestAnimationFrame((time) => this.frame(time));
      else this.draw(0);
    }

    build() {
      const golden = Math.PI * (3 - Math.sqrt(5));
      for (let i = 0; i < this.count; i += 1) {
        const y = 1 - (i / (this.count - 1)) * 2;
        const r = Math.sqrt(Math.max(0, 1 - y * y));
        const theta = golden * i;
        this.nodes.push({
          x: Math.cos(theta) * r + (Math.random() - 0.5) * 0.18,
          y: y + (Math.random() - 0.5) * 0.18,
          z: Math.sin(theta) * r + (Math.random() - 0.5) * 0.18,
          pulse: Math.random() * TAU,
        });
      }
      const seen = new Set();
      this.nodes.forEach((node, index) => {
        const nearest = this.nodes
          .map((other, otherIndex) => ({
            index: otherIndex,
            d: (node.x - other.x) ** 2 + (node.y - other.y) ** 2 + (node.z - other.z) ** 2,
          }))
          .filter((item) => item.index !== index)
          .sort((a, b) => a.d - b.d)
          .slice(0, 2);
        nearest.forEach((item) => {
          const key = index < item.index ? `${index}:${item.index}` : `${item.index}:${index}`;
          if (!seen.has(key)) { seen.add(key); this.edges.push([index, item.index]); }
        });
      });
      for (let i = 0; i < 14; i += 1) {
        const edge = this.edges[Math.floor(Math.random() * this.edges.length)];
        this.pulses.push({ edge, t: Math.random(), speed: 0.004 + Math.random() * 0.006 });
      }
    }

    bind() {
      this.resize = this.resize.bind(this);
      global.addEventListener("resize", this.resize);
      if (global.ResizeObserver) new ResizeObserver(this.resize).observe(this.canvas.parentElement);
    }

    resize() {
      const rect = this.canvas.getBoundingClientRect();
      const dpr = Math.min(2, global.devicePixelRatio || 1);
      this.width = Math.max(320, rect.width);
      this.height = Math.max(220, rect.height);
      this.canvas.width = Math.round(this.width * dpr);
      this.canvas.height = Math.round(this.height * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (reduceMotion) this.draw(0);
    }

    setData(data) {
      this.active = true;
      this.activity = Math.min(1, (data.peak || 0) * 2.4);
      this.share = data.shares ? data.shares[1] : 0.5;
      this.steps = data.steps || 0;
      this.step = 0;
      this.onTick({ step: 0, share: this.share, divergence: data.divergence || 0, active: true });
    }

    frame(time) {
      const delta = Math.min(48, time - (this.last || time));
      this.last = time;
      this.rotation += delta * 0.00016;
      this.timer += delta;
      if (this.timer > 2600) {
        this.timer = 0;
        this.target = Math.floor(Math.random() * this.nodes.length);
      }
      if (time - this.lastTick > 180) {
        this.lastTick = time;
        if (this.active) this.step = (this.step + 1) % Math.max(1, this.steps || 120);
        this.onTick({
          step: this.step,
          share: this.share,
          divergence: this.active ? Math.abs(0.5 - this.share) * 2 : 0,
          active: this.active,
        });
      }
      this.pulses.forEach((pulse) => {
        pulse.t += pulse.speed;
        if (pulse.t > 1) pulse.t = 0;
      });
      this.draw(time);
      requestAnimationFrame((value) => this.frame(value));
    }

    draw(time) {
      const ctx = this.ctx;
      const w = this.width;
      const h = this.height;
      const cx = w / 2;
      const cy = h / 2 + 6;
      const radius = Math.min(w, h) * 0.36;
      ctx.clearRect(0, 0, w, h);

      // perspective floor grid
      ctx.save();
      ctx.strokeStyle = "rgba(34,211,238,.10)";
      ctx.lineWidth = 1;
      for (let i = -4; i <= 4; i += 1) {
        ctx.beginPath();
        ctx.moveTo(cx + i * w * 0.06, h * 0.92);
        ctx.lineTo(cx + i * w * 0.18, h * 0.62);
        ctx.stroke();
      }
      for (let i = 0; i < 5; i += 1) {
        const y = h * 0.62 + i * i * 7;
        ctx.beginPath();
        ctx.moveTo(cx - w * 0.3, y);
        ctx.lineTo(cx + w * 0.3, y);
        ctx.stroke();
      }
      ctx.restore();

      // reticle rings
      ctx.save();
      ctx.translate(cx, cy);
      ctx.strokeStyle = "rgba(34,211,238,.16)";
      [0.5, 0.72, 0.94].forEach((factor, index) => {
        ctx.beginPath();
        ctx.ellipse(0, 0, radius * factor, radius * factor * 0.42, this.rotation * 0.15 + index * 0.2, 0, TAU);
        ctx.stroke();
      });
      ctx.strokeStyle = "rgba(34,211,238,.10)";
      ctx.beginPath();
      ctx.moveTo(-radius * 1.1, 0); ctx.lineTo(radius * 1.1, 0);
      ctx.moveTo(0, -radius * 0.75); ctx.lineTo(0, radius * 0.75);
      ctx.stroke();
      ctx.restore();

      // projected nodes
      const projected = this.nodes.map((node) => project(node, this.rotation, cx, cy, radius));
      const depthOrder = projected.map((point, index) => ({ index, z: point.depth })).sort((a, b) => a.z - b.z);

      // edges
      ctx.lineWidth = 1;
      this.edges.forEach(([a, b]) => {
        const pa = projected[a];
        const pb = projected[b];
        const alpha = Math.min(0.36, 0.06 + (pa.depth + pb.depth) * 0.04);
        ctx.strokeStyle = `rgba(34,211,238,${alpha.toFixed(3)})`;
        ctx.beginPath();
        ctx.moveTo(pa.x, pa.y);
        ctx.lineTo(pb.x, pb.y);
        ctx.stroke();
      });

      // travelling pulses
      this.pulses.forEach((pulse, index) => {
        const [a, b] = pulse.edge;
        const pa = projected[a];
        const pb = projected[b];
        const x = pa.x + (pb.x - pa.x) * pulse.t;
        const y = pa.y + (pb.y - pa.y) * pulse.t;
        ctx.beginPath();
        ctx.fillStyle = index % 3 === 0 ? "rgba(255,176,32,.95)" : "rgba(34,211,238,.95)";
        ctx.shadowColor = ctx.fillStyle;
        ctx.shadowBlur = 8;
        ctx.arc(x, y, 1.6, 0, TAU);
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      // nodes
      const warm = Math.round(this.share * this.count);
      depthOrder.forEach(({ index }) => {
        const point = projected[index];
        const node = this.nodes[index];
        const active = this.active && index % 9 === 0;
        const pulse = 0.6 + 0.4 * Math.sin(time * 0.002 + node.pulse);
        const isWarm = index < warm;
        const color = isWarm ? "255,176,32" : "34,211,238";
        const alpha = Math.min(1, 0.35 + point.depth * 0.22);
        ctx.beginPath();
        ctx.fillStyle = `rgba(${color},${alpha.toFixed(2)})`;
        ctx.shadowColor = `rgba(${color},.9)`;
        ctx.shadowBlur = active ? 12 : 4;
        ctx.arc(point.x, point.y, (active ? 2.4 : 1.6) * point.scale * pulse, 0, TAU);
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      // tracking brackets on a target node
      const target = projected[this.target];
      if (target) {
        const size = 16 + Math.sin(time * 0.004) * 2;
        ctx.strokeStyle = "rgba(255,176,32,.9)";
        ctx.lineWidth = 1.2;
        [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([sx, sy]) => {
          ctx.beginPath();
          ctx.moveTo(target.x + sx * size, target.y + sy * size * 0.7 - sy * 6);
          ctx.lineTo(target.x + sx * size, target.y + sy * size * 0.7);
          ctx.lineTo(target.x + sx * size - sx * 6, target.y + sy * size * 0.7);
          ctx.stroke();
        });
        ctx.fillStyle = "rgba(255,176,32,.85)";
        ctx.font = "9px ui-monospace, monospace";
        ctx.fillText(`TRK-${String(this.target).padStart(3, "0")}`, target.x + 12, target.y - 12);
      }

      // sweeping scan
      const sweep = (time * 0.00012) % 1;
      const gradient = ctx.createLinearGradient(cx - radius, 0, cx + radius, 0);
      gradient.addColorStop(Math.max(0, sweep - 0.12), "rgba(34,211,238,0)");
      gradient.addColorStop(sweep, "rgba(34,211,238,.18)");
      gradient.addColorStop(Math.min(1, sweep + 0.02), "rgba(34,211,238,0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(cx - radius, cy - radius * 0.8, radius * 2, radius * 1.6);
    }
  }

  global.TrackScene = { create: (canvas, options) => new Tracker(canvas, options) };
})(typeof window !== "undefined" ? window : globalThis);
