"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Navbar.module.css";

const links = [
  { href: "/", label: "Producto" },
  { href: "/como-funciona", label: "Cómo funciona" },
];

export default function Navbar() {
  const pathname = usePathname();
  return (
    <nav className={styles.nav}>
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
