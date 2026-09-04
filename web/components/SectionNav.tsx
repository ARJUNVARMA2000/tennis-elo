"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { sectionForPath } from "@/lib/navigation";
import { useTour } from "@/lib/tour";
import { withTour } from "@/lib/url";

export default function SectionNav() {
  const path = usePathname().replace(/\/$/, "");
  const section = sectionForPath(path);
  const { tour } = useTour();
  if (!section) return null;
  return (
    <nav aria-label={`${section.label} sections`} className="mt-5 flex flex-wrap gap-x-5 gap-y-1 border-b border-[var(--color-line)]" data-section-navigation={section.label}>
      {section.items.map((item) => (
        <Link key={item.href} href={withTour(`${item.href}/`, tour)} aria-current={path === item.href ? "page" : undefined}
          className={`border-b-2 px-1 py-3 text-[13px] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] ${path === item.href ? "border-[var(--color-accent)] text-[var(--color-text)]" : "border-transparent text-[var(--color-muted)] hover:text-[var(--color-text)]"}`}>
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
