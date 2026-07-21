import { getArticles } from "@/lib/articles"
import { ArticleList } from "@/components/article-list"

export default async function ItSciencePage() {
  const articles = await getArticles("it-science")

  return (
    <section className="mx-auto max-w-3xl px-4 py-6">
      <ArticleList articles={articles} />
    </section>
  )
}
