import type { CategoryArticle } from "@/lib/articles"

function ArticleCard({ article }: { article: CategoryArticle }) {
  return (
    <li>
      <a
        href={article.link}
        target="_blank"
        rel="noopener noreferrer"
        className="group flex items-start gap-3 px-4 py-3.5 transition-colors hover:bg-accent/40 sm:px-5"
      >
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2 text-xs">
            {article.press && <span className="font-medium text-primary">{article.press}</span>}
            {article.articleDate && <span className="text-muted-foreground">{article.articleDate}</span>}
          </div>
          <h3 className="text-pretty text-[15px] font-medium leading-snug text-card-foreground group-hover:text-primary sm:text-base">
            {article.title}
          </h3>
          {article.summary && (
            <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-muted-foreground">{article.summary}</p>
          )}
        </div>
        {article.thumbnail && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={article.thumbnail || "/placeholder.svg"}
            alt=""
            className="ml-1 h-16 w-24 shrink-0 rounded-md object-cover sm:h-20 sm:w-28"
            loading="lazy"
            referrerPolicy="no-referrer"
          />
        )}
      </a>
    </li>
  )
}

export function ArticleList({ articles }: { articles: CategoryArticle[] }) {
  if (articles.length === 0) {
    return <p className="px-5 py-16 text-center text-sm text-muted-foreground">표시할 기사가 없습니다.</p>
  }
  return (
    <div className="mx-auto w-full max-w-3xl overflow-hidden rounded-xl border border-border bg-card">
      <ul className="divide-y divide-border">
        {articles.map((a) => (
          <ArticleCard key={a.link} article={a} />
        ))}
      </ul>
    </div>
  )
}
