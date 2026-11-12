/* Particle overlays for the three telemetry charts. Decorative, group-level only. */
(function (global) {
  "use strict";
  const reduce = global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches;

  class ParticleField {
    constructor(canvas, chart, mode) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.chart = chart;
      this.mode = mode;
      this.data = null;
      this.particles = [];
      this.running = true;
      this.last = 0;
      this.lastFrame = 0;
      this.resize = this.resize.bind(this);
      this.frame = this.frame.bind(this);
      global.addEventListener("resize", this.resize);
      if (global.ResizeObserver) new ResizeObserver(this.resize).observe(canvas.parentElement);
      this.resize();
      if (!reduce) requestAnimationFrame(this.frame);
    }

    resize() {
      const rect = this.canvas.getBoundingClientRect();
      const dpr = Math.min(2, global.devicePixelRatio || 1);
      this.width = Math.max(10, rect.width);
      this.height = Math.max(10, rect.height);
      this.canvas.width = Math.round(this.width * dpr);
      this.canvas.height = Math.round(this.height * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (this.data) this.seed();
      if (reduce && this.data) this.renderFrame();
    }

    setData(data) {
      this.data = data;
      // Seed once when the first data arrives; keep the cloud stable across
      // replay frames instead of reseeding (and jittering) on every step.
      if (!this.particles.length) this.seed();
      if (reduce) this.renderFrame();
    }

    bounds() {
      try {
        const x0 = this.chart.convertToPixel({ xAxisIndex: 0 }, 0);
        const x1 = this.chart.convertToPixel({ xAxisIndex: 0 }, this.data.length - 1);
        const y0 = this.chart.convertToPixel({ yAxisIndex: 0 }, 0);
        const y1 = this.chart.convertToPixel({ yAxisIndex: 0 }, 1);
        return { left: Math.min(x0, x1), right: Math.max(x0, x1), top: Math.min(y0, y1), bottom: Math.max(y0, y1) };
      } catch {
        return { left: 40, right: this.width - 12, top: 28, bottom: this.height - 28 };
      }
    }

    seed() {
      if (!this.data || !this.data.length) return;
      const count = this.mode === "cascade" ? 34 : 46;
      this.particles = Array.from({ length: count }, () => this.spawn(true));
    }

    spawn(initial = false) {
      if (this.mode === "line") {
        return { t: Math.random() * (this.data.length - 1), speed: 0.008 + Math.random() * 0.02,
                 size: 0.8 + Math.random() * 1.8, warm: Math.random() < 0.15 };
      }
      if (this.mode === "shares") {
        return { x: Math.random(), y: initial ? Math.random() : -0.05,
                 speed: 0.0008 + Math.random() * 0.0025, size: 0.6 + Math.random() * 1.4,
                 warm: Math.random() < 0.5, phase: Math.random() * 6.28 };
      }
      const peak = Math.max(...this.data, 0.001);
      let step = 0;
      for (let tries = 0; tries < 12; tries += 1) {
        const candidate = Math.floor(Math.random() * this.data.length);
        if (Math.random() < this.data[candidate] / peak) { step = candidate; break; }
      }
      return { step, life: initial ? Math.random() : 0, speed: 0.006 + Math.random() * 0.01,
               vx: (Math.random() - 0.5) * 0.06, vy: -(0.2 + Math.random() * 0.8),
               size: 0.8 + Math.random() * 2.1 };
    }

    point(step, value) {
      const x = this.chart.convertToPixel({ xAxisIndex: 0 }, step);
      const y = this.chart.convertToPixel({ yAxisIndex: 0 }, value);
      return [x, y];
    }

    drawLine(bounds) {
      const values = this.data;
      this.particles.forEach((particle) => {
        particle.t += particle.speed;
        if (particle.t > values.length - 1) particle.t = 0;
        const index = Math.floor(particle.t);
        const next = Math.min(values.length - 1, index + 1);
        const frac = particle.t - index;
        const value = values[index] * (1 - frac) + values[next] * frac;
        const [x, y] = this.point(particle.t, value);
        if (!Number.isFinite(x) || !Number.isFinite(y)) return;
        const color = particle.warm ? "255,176,32" : "34,211,238";
        this.ctx.beginPath();
        this.ctx.fillStyle = `rgba(${color},.9)`;
        if (!global.__OPINIONLAB_PLAYBACK__) {
          this.ctx.shadowColor = `rgba(${color},.9)`;
          this.ctx.shadowBlur = 7;
        }
        this.ctx.arc(x, y, particle.size, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.shadowBlur = 0;
        this.ctx.strokeStyle = `rgba(${color},.18)`;
        this.ctx.beginPath();
        this.ctx.moveTo(x - 8, y + 1);
        this.ctx.lineTo(x, y);
        this.ctx.stroke();
      });
    }

    drawShares(bounds) {
      const rows = this.data; // [{share0, share1}]
      const width = bounds.right - bounds.left;
      const height = bounds.bottom - bounds.top;
      this.particles.forEach((particle) => {
        particle.y += particle.speed * 10;
        if (particle.y > 1) { Object.assign(particle, this.spawn()); particle.y = -0.02; }
        const x = bounds.left + particle.x * width + Math.sin(particle.phase + particle.y * 8) * 4;
        const y = bounds.bottom - particle.y * height;
        const row = rows[Math.min(rows.length - 1, Math.floor(particle.x * rows.length))] || [0.5, 0.5];
        const warm = row[1] > row[0];
        const color = warm ? "255,176,32" : "34,211,238";
        this.ctx.beginPath();
        this.ctx.fillStyle = `rgba(${color},.45)`;
        this.ctx.arc(x, y, particle.size, 0, Math.PI * 2);
        this.ctx.fill();
      });
    }

    drawCascade(bounds) {
      const values = this.data;
      const width = bounds.right - bounds.left;
      const height = bounds.bottom - bounds.top;
      this.particles.forEach((particle) => {
        particle.life += particle.speed;
        if (particle.life > 1) Object.assign(particle, this.spawn(), { life: 0 });
        const barX = bounds.left + (particle.step / Math.max(1, values.length - 1)) * width;
        const top = bounds.bottom - (values[particle.step] || 0) * height;
        const x = barX + particle.vx * particle.life * width;
        const y = top + particle.vy * particle.life * height * 0.18;
        const alpha = Math.max(0, 0.7 * (1 - particle.life));
        this.ctx.beginPath();
        this.ctx.fillStyle = `rgba(255,176,32,${alpha.toFixed(2)})`;
        if (!global.__OPINIONLAB_PLAYBACK__) {
          this.ctx.shadowColor = "rgba(255,176,32,.8)";
          this.ctx.shadowBlur = 6;
        }
        this.ctx.arc(x, y, particle.size * (1 - particle.life * 0.5), 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.shadowBlur = 0;
      });
    }

    renderFrame() {
      this.ctx.clearRect(0, 0, this.width, this.height);
      if (this.data && this.data.length && !document.hidden) {
        const bounds = this.bounds();
        this.ctx.save();
        this.ctx.beginPath();
        this.ctx.rect(bounds.left, bounds.top - 8, bounds.right - bounds.left, bounds.bottom - bounds.top + 16);
        this.ctx.clip();
        if (this.mode === "line") this.drawLine(bounds);
        else if (this.mode === "shares") this.drawShares(bounds);
        else this.drawCascade(bounds);
        this.ctx.restore();
      }
    }

    frame(time) {
      if (!this.running) return;
      const fps = global.__OPINIONLAB_PLAYBACK__ ? 12 : 30;
      if (time - this.lastFrame < 1000 / fps) {
        requestAnimationFrame(this.frame);
        return;
      }
      this.lastFrame = time;
      const delta = Math.min(48, time - (this.last || time));
      this.last = time;
      this.renderFrame();
      requestAnimationFrame(this.frame);
    }
  }

  global.TrackParticles = { create: (canvas, chart, mode) => new ParticleField(canvas, chart, mode) };
})(typeof window !== "undefined" ? window : globalThis);
