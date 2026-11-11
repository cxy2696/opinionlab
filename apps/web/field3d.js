/* Three lightweight 3D telemetry fields: terrain, bar array and stance cloud. */
(function (global) {
  "use strict";
  const reduce = global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const TAU = Math.PI * 2;

  function project(x, y, z, angle, cx, cy, scale) {
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    const xr = x * cos - z * sin;
    const zr = x * sin + z * cos;
    const tilt = 0.62;
    const yr = y * Math.cos(tilt) - zr * Math.sin(tilt);
    const depth = y * Math.sin(tilt) + zr * Math.cos(tilt);
    const perspective = 2.4 / (2.4 + depth);
    return { x: cx + xr * scale * perspective, y: cy - yr * scale * perspective, depth, perspective };
  }

  class Field3D {
    constructor(canvas, mode) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.mode = mode;
      this.angle = 0.6;
      this.t = 0;
      this.last = 0;
      this.diversity = [0.5, 0.42, 0.3, 0.18, 0.08, 0.02];
      this.cascade = [0.04, 0.08, 0.12, 0.2, 0.32, 0.18, 0.1, 0.06];
      this.warm = 0.5;
      this.targets = [];
      this.picks = [];
      this.hover = null;
      this.resize = this.resize.bind(this);
      this.frame = this.frame.bind(this);
      global.addEventListener("resize", this.resize);
      if (global.ResizeObserver) new ResizeObserver(this.resize).observe(canvas.parentElement);
      this.resize();
      this.canvas.addEventListener("pointermove", (event) => {
        if (this.mode !== "bars") return;
        const rect = this.canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        let best = null;
        let distance = 22;
        this.picks.forEach((pick) => {
          const d = Math.hypot(pick.x - x, pick.y - y);
          if (d < distance) { distance = d; best = pick; }
        });
        this.hover = best;
      });
      this.canvas.addEventListener("pointerleave", () => { this.hover = null; });
      if (!reduce) requestAnimationFrame(this.frame);
      else this.draw(0);
    }

    resize() {
      const rect = this.canvas.getBoundingClientRect();
      const dpr = Math.min(2, global.devicePixelRatio || 1);
      this.width = Math.max(120, rect.width);
      this.height = Math.max(110, rect.height);
      this.canvas.width = Math.round(this.width * dpr);
      this.canvas.height = Math.round(this.height * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.cx = this.width * 0.5;
      this.cy = this.height * 0.62;
      this.scale = Math.min(this.width * 0.34, this.height * 0.52);
      if (this.mode === "bars" && !this.targets.length) this.buildBars();
      if (reduce) this.draw(0);
    }

    setData(data) {
      if (data.diversity && data.diversity.length) this.diversity = data.diversity.slice(-160);
      if (data.cascade && data.cascade.length) this.cascade = data.cascade.slice(-160);
      if (data.shares && data.shares.length) {
        const last = data.shares[data.shares.length - 1];
        this.warm = last[1] || 0.5;
      }
      if (this.mode === "bars") this.buildBars();
    }

    buildBars() {
      const grid = 8;
      this.targets = [];
      for (let ix = 0; ix < grid; ix += 1) {
        for (let iz = 0; iz < grid; iz += 1) {
          const index = Math.floor((ix / (grid - 1)) * (this.cascade.length - 1));
          const base = this.cascade[Math.max(0, index)] || 0.04;
          const wave = 0.5 + 0.5 * Math.sin(ix * 1.3 + iz * 0.9);
          this.targets.push({
            x: (ix / (grid - 1) - 0.5) * 1.8,
            z: (iz / (grid - 1) - 0.5) * 1.8,
            height: 0.02,
            step: index,
            value: base,
            target: Math.max(0.03, base * (0.55 + wave * 0.9)),
            color: (ix + iz) % 5 === 0 ? "255,176,32" : (ix + iz) % 3 === 0 ? "167,139,250" : "34,211,238",
          });
        }
      }
    }

    frame(time) {
      const delta = Math.min(40, time - (this.last || time));
      this.last = time;
      this.t += delta * 0.001;
      if (!document.hidden) {
        this.draw(this.t);
      }
      requestAnimationFrame(this.frame);
    }

    draw(t) {
      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.width, this.height);
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      if (this.mode === "wave") this.drawWave(ctx, t);
      else if (this.mode === "bars") this.drawBars(ctx, t);
      else this.drawCloud(ctx, t);
      ctx.restore();
    }

    drawHorizon(ctx) {
      const horizon = ctx.createLinearGradient(0, this.cy - 20, 0, this.height);
      horizon.addColorStop(0, "rgba(34,211,238,0)");
      horizon.addColorStop(1, "rgba(34,211,238,.08)");
      ctx.fillStyle = horizon;
      ctx.fillRect(0, this.cy - 20, this.width, this.height - this.cy + 20);
    }

    drawWave(ctx, t) {
      this.drawHorizon(ctx);
      const cols = 42;
      const rows = 18;
      for (let ix = 0; ix < cols; ix += 1) {
        for (let iz = 0; iz < rows; iz += 1) {
          const nx = ix / (cols - 1) - 0.5;
          const nz = iz / (rows - 1) - 0.5;
          const step = Math.floor(Math.abs(nx + 0.5) * (this.diversity.length - 1));
          const base = this.diversity[Math.min(this.diversity.length - 1, step)] || 0.1;
          const wave = 0.06 * Math.sin(ix * 0.5 + t * 1.2 + iz * 0.35) +
            0.03 * Math.sin(iz * 0.8 - t * 0.8);
          const y = (base - 0.12) * 0.9 + wave;
          const point = project(nx * 1.9, y, nz * 1.9, this.angle + t * 0.03,
            this.cx, this.cy, this.scale * 1.5);
          const alpha = 0.18 + point.perspective * 0.55;
          const size = 0.7 + point.perspective * 1.5;
          ctx.fillStyle = `rgba(103,232,249,${alpha.toFixed(2)})`;
          ctx.beginPath();
          ctx.arc(point.x, point.y, size, 0, TAU);
          ctx.fill();
        }
      }
    }

    drawBars(ctx, t) {
      this.drawHorizon(ctx);
      this.targets.forEach((bar) => { bar.height += (bar.target - bar.height) * 0.06; });
      const angle = this.angle + t * 0.08;
      const sorted = this.targets
        .map((bar) => {
          const base = project(bar.x, 0, bar.z, angle, this.cx, this.cy, this.scale * 1.35);
          const top = project(bar.x, bar.height, bar.z, angle, this.cx, this.cy, this.scale * 1.35);
          return { ...bar, base, top };
        })
        .sort((a, b) => a.base.depth - b.base.depth);
      this.picks = sorted.map((bar) => ({ x: bar.top.x, y: bar.top.y, step: bar.step, value: bar.value }));
      sorted.forEach((bar) => {
        const width = 0.09 * this.scale * bar.top.perspective;
        const height = bar.base.y - bar.top.y;
        ctx.fillStyle = `rgba(${bar.color},.18)`;
        ctx.fillRect(bar.top.x - width, bar.top.y, width * 2, height);
        ctx.fillStyle = `rgba(${bar.color},.55)`;
        ctx.beginPath();
        ctx.ellipse(bar.top.x, bar.top.y, width, width * 0.38, 0, 0, TAU);
        ctx.fill();
        ctx.strokeStyle = `rgba(${bar.color},.5)`;
        ctx.lineWidth = 0.6;
        ctx.strokeRect(bar.top.x - width, bar.top.y, width * 2, height);
      });
      if (this.hover) {
        const text = `S${this.hover.step + 1} · ${(this.hover.value * 100).toFixed(0)}%`;
        ctx.font = "600 9px ui-monospace, monospace";
        const width = ctx.measureText(text).width + 10;
        const x = Math.min(this.width - width - 4, Math.max(4, this.hover.x - width / 2));
        const y = Math.max(4, this.hover.y - 26);
        ctx.fillStyle = "rgba(2,7,11,.94)";
        ctx.fillRect(x, y, width, 17);
        ctx.strokeStyle = "rgba(34,211,238,.55)";
        ctx.strokeRect(x, y, width, 17);
        ctx.fillStyle = "#d5edf7";
        ctx.fillText(text, x + 5, y + 12);
      }
    }

    drawCloud(ctx, t) {
      const count = this.width < 420 ? 260 : 520;
      const angle = t * 0.12;
      for (let i = 0; i < count; i += 1) {
        const seed = i * 12.9898;
        const theta = (seed % TAU) + angle;
        const radius = 0.15 + (Math.sin(seed * 1.7) * 0.5 + 0.5) * 0.85;
        const height = Math.sin(seed * 2.3 + t * 0.7) * 0.45;
        const x = Math.cos(theta) * radius;
        const z = Math.sin(theta) * radius;
        const point = project(x, height, z, this.angle + t * 0.04, this.cx, this.cy, this.scale * 1.7);
        const warm = (i / count) < this.warm;
        const color = warm ? "255,176,32" : "103,232,249";
        const alpha = 0.14 + point.perspective * 0.45;
        ctx.fillStyle = `rgba(${color},${alpha.toFixed(2)})`;
        ctx.beginPath();
        ctx.arc(point.x, point.y, 0.55 + point.perspective * 1.2, 0, TAU);
        ctx.fill();
      }
      // orbit ring
      ctx.strokeStyle = "rgba(34,211,238,.18)";
      ctx.beginPath();
      ctx.ellipse(this.cx, this.cy, this.scale * 1.15, this.scale * 0.42, 0, 0, TAU);
      ctx.stroke();
    }
  }

  global.TrackField = { create: (canvas, mode) => new Field3D(canvas, mode) };
})(typeof window !== "undefined" ? window : globalThis);
