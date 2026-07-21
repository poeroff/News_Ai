import type { RankingArticle, RankingResult } from "@/lib/ranking"

function OutletCard({ outletName, articles }: { outletName: string; articles: RankingArticle[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="border-b border-border px-4 py-2.5">
        <h2 className="text-sm font-bold text-card-foreground">{outletName}</h2>
      </div>
      <ol className="divide-y divide-border">
        {articles.map((a) => (
          <li key={a.link}>
            <a
              href={a.link}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-start gap-2.5 px-4 py-2.5 transition-colors hover:bg-accent/40"
            >
              <span
                className={`shrink-0 text-sm font-bold tabular-nums ${
                  a.rank <= 3 ? "text-primary" : "text-muted-foreground"
                }`}
              >
                {a.rank}
              </span>
              <span className="min-w-0 flex-1 text-pretty text-sm leading-snug text-card-foreground line-clamp-2 group-hover:text-primary">
                {a.title}
              </span>
              {a.thumbnail && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={a.thumbnail || "/placeholder.svg"}
                  alt=""
                  className="h-12 w-14 shrink-0 rounded-md object-cover"
                  loading="lazy"
                  referrerPolicy="no-referrer"
                />
              )}
            </a>
          </li>
        ))}
      </ol>
    </div>
  )
}

export function NewsRanking({ data }: { data: RankingResult }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {data.outlets.map((outletName) => (
        <OutletCard key={outletName} outletName={outletName} articles={data.byOutlet[outletName]} />
      ))}
    </div>
  )
}
