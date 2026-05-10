"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Navbar.module.css";

const links = [
  { href: "/", label: "Demo" },
  { href: "/como-funciona", label: "Cómo funciona" },
];

export default function Navbar() {
  const pathname = usePathname();
  return (
    <nav className={styles.nav}>
      <Link href="/" className={styles.brand} aria-label="verbalize home">
        <svg
          width="240"
          height="60"
          viewBox="0 0 480 120"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <g transform="translate(30, 30)">
            <rect x="0" y="22" width="42" height="6" rx="1.5" fill="#e6e6e6" opacity="0.25" />
            <rect x="0" y="32" width="50" height="6" rx="1.5" fill="#e6e6e6" opacity="0.4" />
            <rect x="0" y="42" width="58" height="6" rx="1.5" fill="#e6e6e6" opacity="0.55" />
            <line x1="-3" y1="51" x2="69" y2="51" stroke="#cc785c" strokeWidth="0.5" strokeDasharray="2 2" opacity="0.6" />
            <rect x="0" y="52" width="66" height="6" rx="1.5" fill="#cc785c" />
            <line x1="-3" y1="61" x2="72" y2="61" stroke="#cc785c" strokeWidth="0.5" strokeDasharray="2 2" opacity="0.6" />
            <circle cx="78" cy="55" r="3" fill="#cc785c" />
            <circle cx="88" cy="55" r="3" fill="#cc785c" opacity="0.7" />
            <circle cx="98" cy="55" r="3" fill="#cc785c" opacity="0.5" />
          </g>
          <text
            x="145"
            y="80"
            fontFamily="-apple-system, Inter, sans-serif"
            fontWeight="600"
            fontSize="54"
            fill="#e6e6e6"
            letterSpacing="-0.5"
          >
            verbalize
          </text>
        </svg>
      </Link>
      <div className={styles.links}>
        {links.map((l) => {
          const active = pathname === l.href;
          return (
            <Link
              key={l.href}
              href={l.href}
              className={`${styles.link} ${active ? styles.active : ""}`}
            >
              {l.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
