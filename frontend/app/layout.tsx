import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Noto_Sans_KR, Noto_Serif_KR } from 'next/font/google'
import './globals.css'
import { getRanking } from '@/lib/ranking'
import { SiteNav } from '@/components/site-nav'

const notoSans = Noto_Sans_KR({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  variable: '--font-sans',
})

const notoSerif = Noto_Serif_KR({
  subsets: ['latin'],
  weight: ['600', '700', '900'],
  variable: '--font-serif',
})

export const metadata: Metadata = {
  title: '뉴스랭크 | 언론사별 실시간 뉴스 랭킹',
  description: '연합뉴스, 한국경제, 동아일보, 경향신문, SBS 등 주요 언론사의 실시간 주요 기사 랭킹을 한눈에.',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  colorScheme: 'light dark',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: 'white' },
    { media: '(prefers-color-scheme: dark)', color: 'black' },
  ],
}

function formatUpdated(iso: string): string {
  const d = new Date(iso)
  return new Intl.DateTimeFormat('ko-KR', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(d)
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const data = await getRanking()

  return (
    <html lang="ko" className={`bg-background ${notoSans.variable} ${notoSerif.variable}`}>
      <body className="antialiased font-sans">
        <main className="min-h-dvh">
          <header className="border-b border-border bg-card">
            <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-5">
              <div className="flex items-center gap-2.5">
                <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-lg font-black text-primary-foreground font-serif">
                  N
                </span>
                <div>
                  <h1 className="text-xl font-bold leading-none tracking-tight font-serif">NewsScent</h1>
                  <p className="mt-1 text-xs text-muted-foreground">뉴스를 통한 지식 공유</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">업데이트</p>
                <p className="text-sm font-medium tabular-nums">{formatUpdated(data.updatedAt)}</p>
              </div>
            </div>
            <div className="mx-auto max-w-7xl px-3 sm:px-0">
              <SiteNav />
            </div>
          </header>

          {children}

          <footer className="mx-auto max-w-7xl px-4 pb-10 pt-4">
            <p className="text-xs leading-relaxed text-muted-foreground">
              기사 데이터는 네이버 뉴스 언론사별 랭킹 페이지에서 실시간으로 수집되며 10분마다 갱신됩니다. 모든
              기사의 저작권은 해당 언론사에 있습니다.
            </p>
          </footer>
        </main>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
