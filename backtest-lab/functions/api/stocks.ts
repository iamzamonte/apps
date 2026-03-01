import YahooFinance from 'yahoo-finance2'

interface StockPrice {
  date: string
  close: number
}

function toDateString(date: Date): string {
  return new Date(date).toISOString().slice(0, 10)
}

function errorResponse(message: string, status = 400): Response {
  return Response.json({ error: message }, { status })
}

export const onRequestGet: PagesFunction = async (context) => {
  const url = new URL(context.request.url)
  const symbolsParam = url.searchParams.get('symbols')
  const startDate = url.searchParams.get('startDate')
  const endDate = url.searchParams.get('endDate')

  if (!symbolsParam || !startDate || !endDate) {
    return errorResponse('Missing required parameters: symbols, startDate, endDate')
  }

  const symbols = symbolsParam
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)

  if (symbols.length === 0) {
    return errorResponse('No valid symbols provided')
  }

  if (symbols.length > 10) {
    return errorResponse('Maximum 10 symbols allowed')
  }

  try {
    const yahooFinance = new YahooFinance()
    const results: Record<string, StockPrice[]> = {}

    await Promise.all(
      symbols.map(async (symbol) => {
        const data = await yahooFinance.chart(symbol, {
          period1: startDate,
          period2: endDate,
          interval: '1d',
        })

        results[symbol] = (data.quotes ?? [])
          .filter((q) => q.close !== null && q.close !== undefined)
          .map((q) => ({
            date: toDateString(q.date),
            close: q.close as number,
          }))
      })
    )

    return Response.json(results, {
      headers: {
        'Cache-Control': 'public, max-age=3600, s-maxage=86400',
        'Access-Control-Allow-Origin': '*',
      },
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to fetch stock data'
    console.error('Yahoo Finance API error:', message)
    return errorResponse(message, 502)
  }
}
