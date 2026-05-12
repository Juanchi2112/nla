"use client";

import { useEffect, useState } from "react";

const generateValue = () => {
  const v = (Math.random() * 4 - 2).toFixed(3);
  return v.startsWith("-") ? v : " " + v;
};

const buildMatrix = (size: number) => {
  return Array.from({ length: size }, () => generateValue());
};

export default function FlickeringMatrix({ rows = 8, cols = 8 }: { rows?: number; cols?: number }) {
  const size = rows * cols;
  const [matrix, setMatrix] = useState<string[]>(() => buildMatrix(size));

  useEffect(() => {
    const interval = setInterval(() => {
      const count = Math.floor(size / 4);
      setMatrix((prev) => {
        const next = [...prev];
        for (let i = 0; i < count; i++) {
          const idx = Math.floor(Math.random() * size);
          next[idx] = generateValue();
        }
        return next;
      });
    }, 150);
    return () => clearInterval(interval);
  }, [size]);

  return (
    <div 
      className="grid gap-1 font-mono text-[9px] leading-none text-primary/40"
      style={{ 
        gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` 
      }}
    >
      {matrix.map((v, i) => {
        const num = parseFloat(v);
        const isHigh = Math.abs(num) > 1.2;
        return (
          <span 
            key={i} 
            className={`transition-colors duration-200 ${isHigh ? "text-primary font-bold" : ""}`}
          >
            {v}
          </span>
        );
      })}
    </div>
  );
}
