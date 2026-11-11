/* Immersive galaxy backdrop for the cockpit hero. Decorative only. */
(function (global) {
  "use strict";
  const reduce = global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches;

  class Galaxy {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.angle = 0;
      this.last = 0;
      this.resize = this.resize.bind(this);
      this.frame = this.frame.bind(this);
      global.addEventListener("resize", this.resize);
      if (global.ResizeObserver) new ResizeObserver(this.resize).observe(canvas.parentElement);
      this.build();
      this.resize();
      if (!reduce) requestAnimationFrame(this.frame);
      else this.draw(0);
    }

    build() {
      const stars = Math.min(520, Math.max(220, Math.floor(global.innerWidth / 2.4)));
      this.stars = Array.from({ length: stars }, () => ({
        x: Math.random(), y: Math.random(),
        size: Math.random() < 0.08 ? 1.6 : 0.4 + Math.random() * 1.0,
        alpha: 0.2 + Math.random() * 0.7,
        phase: Math.random() * Math.PI * 2,
      }));
      this.dust = Array.from({ length: 1200 }, () => {
        const radius = Math.pow(Math.random(), 0.62);
        return {
          radius,
          arm: Math.floor(Math.random() * 3),
          spread: (Math.random() - 0.5) * (0.12 + radius * 0.34),
          size: 0.5 + Math.random() * 2.4,
          alpha: 0.24 + Math.random() * 0.76,
          warm: Math.random() < 0.16,
        };
      });
      this.shooting = null;
      this.nextShoot = 2 + Math.random() * 5;
    }

    resize() {
      const rect = this.canvas.getBoundingClientRect();
      const dpr = Math.min(2, global.devicePixelRatio || 1);
      this.width = Math.max(320, rect.width);
      this.height = Math.max(260, rect.height);
      this.canvas.width = Math.round(this.width * dpr);
      this.canvas.height = Math.round(this.height * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.cx = this.width * 0.38;
      this.cy = this.height * 0.52;
      this.maxR = Math.min(this.width, this.height) * 0.78;
      if (reduce) this.draw(0);
    }

    frame(time) {
      const delta = Math.min(50, time - (this.last || time));
      this.last = time;
      this.angle += delta * 0.000045;
      this.draw(time);
      requestAnimationFrame(this.frame);
    }

    draw(time) {
      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.width, this.height);
      ctx.save();
      ctx.globalCompositeOperation = "lighter";

      // star field
      this.stars.forEach((star) => {
        const twinkle = 0.55 + 0.45 * Math.sin(time * 0.001 + star.phase);
        ctx.fillStyle = `rgba(186,230,253,${(star.alpha * twinkle).toFixed(2)})`;
        ctx.beginPath();
        ctx.arc(star.x * this.width, star.y * this.height, star.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // galactic core
      const core = ctx.createRadialGradient(this.cx, this.cy, 0, this.cx, this.cy, this.maxR * 0.42);
      core.addColorStop(0, "rgba(240,255,255,.98)");
      core.addColorStop(0.14, "rgba(125,240,255,.82)");
      core.addColorStop(0.42, "rgba(20,150,180,.30)");
      core.addColorStop(1, "rgba(3,10,18,0)");
      ctx.fillStyle = core;
      ctx.beginPath();
      ctx.arc(this.cx, this.cy, this.maxR * 0.5, 0, Math.PI * 2);
      ctx.fill();

      // faint elliptical arms
      ctx.strokeStyle = "rgba(103,232,249,.07)";
      for (let ring = 1; ring <= 4; ring += 1) {
        ctx.beginPath();
        ctx.ellipse(this.cx, this.cy, this.maxR * ring * 0.18, this.maxR * ring * 0.08,
                    this.angle * 0.6 + ring * 0.4, 0, Math.PI * 2);
        ctx.stroke();
      }

      // spiral dust
      this.dust.forEach((particle) => {
        const radius = particle.radius * this.maxR;
        const twist = particle.radius * 5.2;
        const theta = this.angle + particle.arm * (Math.PI * 2 / 3) + twist + particle.spread;
        const x = this.cx + Math.cos(theta) * radius;
        const y = this.cy + Math.sin(theta) * radius * 0.46;
        const color = particle.warm ? "255,176,32" : "103,232,249";
        const alpha = particle.alpha * (0.35 + (1 - particle.radius) * 0.65);
        ctx.fillStyle = `rgba(${color},${alpha.toFixed(2)})`;
        ctx.beginPath();
        ctx.arc(x, y, particle.size * (1.25 - particle.radius * 0.55), 0, Math.PI * 2);
        ctx.fill();
      });

      // shooting star
      this.nextShoot -= 0.016;
      if (!this.shooting && this.nextShoot <= 0) {
        this.shooting = { x: this.width * (0.2 + Math.random() * 0.5), y: this.height * Math.random() * 0.4,
                          life: 0, length: 90 + Math.random() * 120 };
        this.nextShoot = 5 + Math.random() * 7;
      }
      if (this.shooting) {
        const s = this.shooting;
        s.life += 0.018;
        const alpha = Math.max(0, 0.75 * (1 - s.life));
        const gradient = ctx.createLinearGradient(s.x, s.y, s.x - s.length, s.y + s.length * 0.45);
        gradient.addColorStop(0, `rgba(255,255,255,${alpha})`);
        gradient.addColorStop(1, "rgba(34,211,238,0)");
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(s.x - s.length, s.y + s.length * 0.45);
        ctx.stroke();
        if (s.life >= 1) this.shooting = null;
      }
      ctx.restore();
    }
  }

  global.TrackGalaxy = { create: (canvas) => new Galaxy(canvas) };
})(typeof window !== "undefined" ? window : globalThis);
