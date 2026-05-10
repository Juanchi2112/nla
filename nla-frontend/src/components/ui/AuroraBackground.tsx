"use client";

import styles from "./AuroraBackground.module.css";

interface AuroraBackgroundProps {
  showRadialGradient?: boolean;
  className?: string;
}

export function AuroraBackground({
  showRadialGradient = true,
  className,
}: AuroraBackgroundProps) {
  return (
    <div
      className={`${styles.root}${className ? ` ${className}` : ""}`}
      aria-hidden
    >
      <div
        className={`${styles.aurora}${showRadialGradient ? ` ${styles.mask}` : ""}`}
      />
    </div>
  );
}
