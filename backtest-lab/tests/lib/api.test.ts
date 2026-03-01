import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchStockData } from '../../src/lib/api'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

beforeEach(() => {
  mockFetch.mockReset()
})

describe('fetchStockData', () => {
  it('calls correct URL with params', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ AAPL: [] }),
    })

    await fetchStockData(['AAPL'], '2024-01-01', '2024-12-31')

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/stocks?symbols=AAPL&startDate=2024-01-01&endDate=2024-12-31'
    )
  })

  it('returns parsed stock data', async () => {
    const mockData = {
      AAPL: [{ date: '2024-01-02', close: 185.5 }],
    }
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const result = await fetchStockData(['AAPL'], '2024-01-01', '2024-12-31')
    expect(result).toEqual(mockData)
  })

  it('throws on error response', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 502,
      json: () => Promise.resolve({ error: 'Failed to fetch' }),
    })

    await expect(
      fetchStockData(['AAPL'], '2024-01-01', '2024-12-31')
    ).rejects.toThrow('Failed to fetch')
  })

  it('joins multiple symbols with comma', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    })

    await fetchStockData(['AAPL', '005930.KS'], '2024-01-01', '2024-12-31')

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('symbols=AAPL%2C005930.KS')
  })

  it('handles error response with no JSON body', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error('Invalid JSON')),
    })

    await expect(
      fetchStockData(['AAPL'], '2024-01-01', '2024-12-31')
    ).rejects.toThrow('Unknown error')
  })

  it('handles error response with no error field', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 400,
      json: () => Promise.resolve({}),
    })

    await expect(
      fetchStockData(['AAPL'], '2024-01-01', '2024-12-31')
    ).rejects.toThrow('HTTP 400')
  })
})
