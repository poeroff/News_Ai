"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

const NAV_ITEMS = [
  { href: "/", name: "홈" },
  { href: "/economy", name: "경제" },
  { href: "/world", name: "세계" },
  { href: "/it-science", name: "IT/과학" },
  { href: "/ranking", name: "랭킹" },
]

export function SiteNav() {
  const pathname = usePathname()

  return (
    <nav
      className="flex gap-1 overflow-x-auto px-1 py-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      aria-label="카테고리"
    >
      {NAV_ITEMS.map((item) => {
        const isActive = pathname === item.href
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={isActive ? "true" : undefined}
            className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              isActive
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
            }`}
          >
            {item.name}
          </Link>
        )
      })}
    </nav>
  )
}
