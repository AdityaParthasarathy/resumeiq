/* Site-wide floating particle field: a pseudo-3D cloud that rotates slowly
   and bobs on a buoyant drift, drawn on one fixed canvas behind all content.
   Colours follow the theme (html.dark) and the brand palette. */
(function () {
    "use strict";

    const canvas = document.getElementById("bg-particles");
    if (!canvas || !canvas.getContext) return;
    const ctx = canvas.getContext("2d");
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // [r, g, b] per theme; indigo (brand) with an occasional amber (logo accent).
    const PALETTE = {
        light: { main: [79, 70, 229], accent: [217, 119, 6], alpha: 0.8 },
        dark: { main: [165, 180, 252], accent: [251, 191, 36], alpha: 0.95 },
    };

    let w = 0, h = 0, dpr = 1, particles = [], raf = 0, last = 0, angle = 0;

    function build() {
        const count = Math.round(Math.min(150, Math.max(55, (w * h) / 11000)));
        particles = [];
        for (let i = 0; i < count; i++) {
            particles.push({
                x: (Math.random() * 2 - 1) * 1.4,
                y: (Math.random() * 2 - 1),
                z: (Math.random() * 2 - 1) * 1.4,
                size: 0.8 + Math.random() * 1.8,
                phase: Math.random() * Math.PI * 2,
                speed: 0.3 + Math.random() * 0.5,
                accent: Math.random() < 0.12,
            });
        }
    }

    function resize() {
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        w = window.innerWidth;
        h = window.innerHeight;
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        build();
        draw(0);
    }

    function draw(t) {
        const theme = document.documentElement.classList.contains("dark") ? PALETTE.dark : PALETTE.light;
        const cos = Math.cos(angle), sin = Math.sin(angle);
        const scale = Math.max(w, h) * 0.55;
        const cx = w / 2, cy = h / 2;
        ctx.clearRect(0, 0, w, h);

        for (const p of particles) {
            // Rotate around the Y axis, then add a gentle vertical bob.
            const rx = p.x * cos - p.z * sin;
            const rz = p.x * sin + p.z * cos;
            const ry = p.y + Math.sin(t * 0.0004 * p.speed * 2 + p.phase) * 0.06;

            const depth = 2.6 / (2.6 + rz);          // perspective factor
            const sx = cx + rx * scale * depth;
            const sy = cy + ry * scale * depth * 0.9;
            if (sx < -20 || sx > w + 20 || sy < -20 || sy > h + 20) continue;

            const c = p.accent ? theme.accent : theme.main;
            const a = theme.alpha * Math.min(1, Math.max(0.12, depth - 0.35));
            ctx.beginPath();
            ctx.arc(sx, sy, p.size * depth * 1.8, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a.toFixed(3) + ")";
            ctx.fill();
        }
    }

    function frame(now) {
        const dt = last ? Math.min(now - last, 50) : 16;
        last = now;
        angle += dt * 0.00006;
        draw(now);
        raf = requestAnimationFrame(frame);
    }

    function start() {
        if (reduced || raf) return;
        last = 0;
        raf = requestAnimationFrame(frame);
    }
    function stop() {
        cancelAnimationFrame(raf);
        raf = 0;
    }

    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
    // Repaint the static frame when the theme flips (reduced-motion has no loop).
    new MutationObserver(() => draw(performance.now()))
        .observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

    resize();
    start();
})();
