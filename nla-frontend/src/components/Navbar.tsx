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
          width="500"
          height="160"
          viewBox="0 0 500 160"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <g transform="translate(60, 80)">
            <path d="M -5 -4 C -16 -14, -22 -22, -26 -32" stroke="#cc785c" strokeWidth="4.5" fill="none" strokeLinecap="round" />
            <path d="M -26 -32 C -30 -36, -32 -36, -34 -32" stroke="#cc785c" strokeWidth="3" fill="none" strokeLinecap="round" />
            <path d="M -26 -32 C -22 -36, -22 -40, -20 -42" stroke="#cc785c" strokeWidth="3" fill="none" strokeLinecap="round" />
            <path d="M -7 0 C -22 -2, -32 -2, -38 0" stroke="#cc785c" strokeWidth="4.5" fill="none" strokeLinecap="round" />
            <path d="M -38 0 C -42 -3, -44 -3, -46 0" stroke="#cc785c" strokeWidth="3" fill="none" strokeLinecap="round" />
            <path d="M -38 0 C -42 3, -44 3, -46 4" stroke="#cc785c" strokeWidth="3" fill="none" strokeLinecap="round" />
            <path d="M -5 4 C -16 14, -22 22, -26 32" stroke="#cc785c" strokeWidth="4.5" fill="none" strokeLinecap="round" />
            <path d="M -26 32 C -30 36, -32 36, -34 32" stroke="#cc785c" strokeWidth="3" fill="none" strokeLinecap="round" />
            <path d="M -26 32 C -22 36, -22 40, -20 42" stroke="#cc785c" strokeWidth="3" fill="none" strokeLinecap="round" />
            <circle cx="0" cy="0" r="11" fill="#cc785c" />
            <path d="M 9 1 C 28 1, 48 0, 64 4" stroke="#cc785c" strokeWidth="4.5" fill="none" strokeLinecap="round" />
            <path d="M 64 4 C 70 0, 74 -2, 76 -4" stroke="#cc785c" strokeWidth="3" fill="none" strokeLinecap="round" />
            <path d="M 64 4 C 70 8, 72 12, 72 16" stroke="#cc785c" strokeWidth="3" fill="none" strokeLinecap="round" />
            <circle cx="77" cy="-5" r="3" fill="#e8a987" />
            <circle cx="73" cy="17" r="3" fill="#e8a987" />
          </g>
          <text
            x="170"
            y="98"
            fontFamily="-apple-system, Inter, sans-serif"
            fontWeight="600"
            fontSize="56"
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
