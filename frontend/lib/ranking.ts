export type RankingArticle = {
  rank: number
  title: string
  link: string
  timeText: string
  thumbnail: string | null
  outletName: string
}

type RankingOutletApi = {
  outletName: string
  articles: Omit<RankingArticle, "outletName">[]
}

type RankingApiResponse = {
  outlets: RankingOutletApi[]
  updatedAt: string
}

export type RankingResult = {
  outlets: string[]
  byOutlet: Record<string, RankingArticle[]>
  updatedAt: string
}

const API_URL = process.env.API_URL || "http://localhost:8000"

// 네이버 랭킹 박스는 언론사당 최대 5개 기사를 보여주는데, 크롤링 시점에 따라
// 일부 언론사는 2~4개만 잡히는 경우가 있어 목록이 허전해 보인다. 꽉 찬(5개) 언론사만 노출한다.
const MIN_ARTICLES_PER_OUTLET = 5

export async function getRanking(): Promise<RankingResult> {
  const res = await fetch(`${API_URL}/ranking`, { next: { revalidate: 600 } })
  if (!res.ok) {
    throw new Error(`랭킹 API 호출 실패: ${res.status}`)
  }
  const data: RankingApiResponse = await res.json()

  const outlets: string[] = []
  const byOutlet: Record<string, RankingArticle[]> = {}

  for (const box of data.outlets) {
    if (box.articles.length < MIN_ARTICLES_PER_OUTLET) continue
    outlets.push(box.outletName)
    byOutlet[box.outletName] = box.articles.map((a) => ({ ...a, outletName: box.outletName }))
  }

  return { outlets, byOutlet, updatedAt: data.updatedAt }
}
