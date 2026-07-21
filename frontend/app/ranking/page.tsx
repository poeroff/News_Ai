import { getRanking } from "@/lib/ranking"
import { NewsRanking } from "@/components/news-ranking"

export default async function RankingPage() {
  const data = await getRanking()

  return (
    <section className="mx-auto max-w-7xl px-4 py-6">
      <NewsRanking data={data} />
    </section>
  )
}
