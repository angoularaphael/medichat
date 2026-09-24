import { useEffect, useRef, useState } from "react";

type Props = { onDone: () => void };

const DURATION = 14;

export default function ArrivalIntro({ onDone }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const doneRef = useRef(onDone);
  const [left, setLeft] = useState(false);
  doneRef.current = onDone;

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      doneRef.current();
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let frame = 0;
    let stopped = false;
    const stars = Array.from({ length: 180 }, () => ({
      x: Math.random(),
      y: Math.random(),
      z: 0.2 + Math.random() * 0.8,
      r: Math.random() * 1.4,
    }));

    const fit = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(canvas.clientWidth * dpr);
      canvas.height = Math.floor(canvas.clientHeight * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    fit();
    window.addEventListener("resize", fit);

    const started = performance.now();

    const sphere = (
      x: number,
      y: number,
      radius: number,
      core: string,
      edge: string,
      light: string,
    ) => {
      const glow = ctx.createRadialGradient(x - radius * 0.35, y - radius * 0.35, radius * 0.1, x, y, radius);
      glow.addColorStop(0, light);
      glow.addColorStop(0.45, core);
      glow.addColorStop(1, edge);
      ctx.beginPath();
      ctx.fillStyle = glow;
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
    };

    const draw = (now: number) => {
      if (stopped) return;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      const t = Math.min(1, (now - started) / (DURATION * 1000));
      const time = (now - started) / 1000;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#02030c";
      ctx.fillRect(0, 0, w, h);

      stars.forEach((star) => {
        const drift = (time * 0.012 * star.z) % 1;
        const x = ((star.x + drift) % 1) * w;
        const y = star.y * h;
        ctx.globalAlpha = 0.25 + star.z * 0.7;
        ctx.fillStyle = "#d7e4ff";
        ctx.beginPath();
        ctx.arc(x, y, star.r, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.globalAlpha = 1;

      const travel = t < 0.72 ? t / 0.72 : 1;
      const pull = t < 0.72 ? 0 : (t - 0.72) / 0.28;
      const cx = w * (0.5 + Math.sin(travel * Math.PI) * 0.08);
      const cy = h * (0.52 - travel * 0.06);

      const earthR = Math.min(w, h) * (0.42 - travel * 0.28) * (1 - pull * 0.35);
      const earthX = cx - w * travel * 0.22;
      const earthY = cy + h * 0.08;
      if (earthR > 8) {
        ctx.save();
        ctx.globalAlpha = 0.35;
        sphere(earthX, earthY, earthR * 1.18, "rgba(80,170,255,0.2)", "transparent", "rgba(140,220,255,0.35)");
        ctx.restore();
        sphere(earthX, earthY, earthR, "#1d62c4", "#071428", "#b7e6ff");
        ctx.save();
        ctx.beginPath();
        ctx.arc(earthX, earthY, earthR, 0, Math.PI * 2);
        ctx.clip();
        ctx.fillStyle = "rgba(18, 90, 62, 0.55)";
        ctx.beginPath();
        ctx.ellipse(earthX - earthR * 0.15 + Math.sin(time * 0.25) * earthR * 0.2, earthY, earthR * 0.45, earthR * 0.22, 0.4, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
        const moonA = time * 0.7;
        const moonX = earthX + Math.cos(moonA) * earthR * 1.7;
        const moonY = earthY + Math.sin(moonA) * earthR * 0.55;
        sphere(moonX, moonY, Math.max(6, earthR * 0.22), "#c5c8d2", "#5c616c", "#f4f6fb");
      }

      const saturnIn = Math.max(0, Math.min(1, (travel - 0.28) / 0.35));
      const saturnR = Math.min(w, h) * 0.16 * saturnIn * (1 - pull * 0.2);
      const saturnX = w * (1.15 - saturnIn * 0.62);
      const saturnY = h * 0.38;
      if (saturnR > 4) {
        ctx.save();
        ctx.translate(saturnX, saturnY);
        ctx.rotate(-0.35);
        ctx.strokeStyle = "rgba(232, 206, 150, 0.85)";
        ctx.lineWidth = Math.max(2, saturnR * 0.08);
        ctx.beginPath();
        ctx.ellipse(0, 0, saturnR * 2.1, saturnR * 0.55, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.strokeStyle = "rgba(180, 150, 90, 0.45)";
        ctx.lineWidth = Math.max(1, saturnR * 0.03);
        ctx.beginPath();
        ctx.ellipse(0, 0, saturnR * 2.45, saturnR * 0.68, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
        sphere(saturnX, saturnY, saturnR, "#e6c98a", "#8a6230", "#fff1c9");
      }

      const nepIn = Math.max(0, Math.min(1, (travel - 0.55) / 0.3));
      const nepR = Math.min(w, h) * 0.2 * nepIn;
      const nepX = w * (0.22 + nepIn * 0.18);
      const nepY = h * (0.78 - nepIn * 0.12);
      if (nepR > 4) {
        ctx.save();
        ctx.globalAlpha = 0.4;
        sphere(nepX, nepY, nepR * 1.25, "rgba(70,90,255,0.25)", "transparent", "rgba(160,180,255,0.3)");
        ctx.restore();
        sphere(nepX, nepY, nepR, "#2436c9", "#070b28", "#9eb0ff");
      }

      if (pull > 0) {
        const sunX = w * 0.5;
        const sunY = h * 0.5;
        sphere(sunX, sunY, 10 + pull * 8, "#ffe7a3", "#c47a22", "#fff8df");
        const bodies = [
          { orbit: 0.12, size: 5, color: "#d9d3c7", speed: 1.4, tilt: 0.2 },
          { orbit: 0.2, size: 8, color: "#3d8dff", speed: 0.85, tilt: 0.35 },
          { orbit: 0.3, size: 6, color: "#d06a45", speed: 0.62, tilt: 0.15 },
          { orbit: 0.42, size: 14, color: "#e6c98a", speed: 0.38, tilt: 0.28 },
          { orbit: 0.56, size: 11, color: "#3150e6", speed: 0.24, tilt: 0.22 },
        ];
        bodies.forEach((body, index) => {
          const angle = time * body.speed + index;
          const rx = Math.min(w, h) * body.orbit * pull;
          const ry = rx * body.tilt;
          const x = sunX + Math.cos(angle) * rx;
          const y = sunY + Math.sin(angle) * ry;
          ctx.globalAlpha = 0.35 * pull;
          ctx.strokeStyle = "rgba(180, 200, 255, 0.45)";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.ellipse(sunX, sunY, rx, ry, 0, 0, Math.PI * 2);
          ctx.stroke();
          ctx.globalAlpha = pull;
          sphere(x, y, body.size * pull, body.color, "#05060f", "#ffffff");
          if (index === 3) {
            ctx.save();
            ctx.translate(x, y);
            ctx.rotate(-0.4);
            ctx.strokeStyle = "rgba(232, 206, 150, 0.8)";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.ellipse(0, 0, body.size * 2.2 * pull, body.size * 0.6 * pull, 0, 0, Math.PI * 2);
            ctx.stroke();
            ctx.restore();
          }
        });
        ctx.globalAlpha = 1;
      }

      frame = requestAnimationFrame(draw);
      if (t >= 1) {
        stopped = true;
        cancelAnimationFrame(frame);
        setLeft(true);
        window.setTimeout(() => doneRef.current(), 700);
      }
    };

    frame = requestAnimationFrame(draw);
    return () => {
      stopped = true;
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", fit);
    };
  }, []);

  return (
    <div className={`arrival ${left ? "arrival-leave" : ""}`} role="presentation">
      <canvas ref={canvasRef} className="arrival-canvas" />
      <button type="button" className="arrival-skip" onClick={onDone}>
        Entrer
      </button>
    </div>
  );
}
