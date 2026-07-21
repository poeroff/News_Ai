export type CategoryArticle = {
  title: string
  link: string
  summary: string | null
  press: string | null
  thumbnail: string | null
  articleDate: string | null
}

export type Category = "home" | "economy" | "world" | "it-science"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function getArticles(category: Category): Promise<CategoryArticle[]> {
  const res = await fetch(`${API_URL}/articles/${category}`, { next: { revalidate: 60 } })
  if (!res.ok) {
    throw new Error(`기사 API 호출 실패: ${res.status}`)
  }
  return res.json()
}
