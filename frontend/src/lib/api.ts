import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const portfolioApi = {
  list: () => api.get('/portfolios').then(r => r.data),
  create: (data: { name: string; description?: string }) =>
    api.post('/portfolios', data).then(r => r.data),
  getPositions: (id: number) => api.get(`/portfolios/${id}/positions`).then(r => r.data),
  addPosition: (id: number, data: object) =>
    api.post(`/portfolios/${id}/positions`, data).then(r => r.data),
  updatePosition: (id: number, data: object) =>
    api.put(`/positions/${id}`, data).then(r => r.data),
  deletePosition: (id: number) => api.delete(`/positions/${id}`),
  importCsv: (id: number, file: File, replace = false) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/portfolios/${id}/import-csv`, form, {
      params: { replace },
    }).then(r => r.data)
  },
}

export const analyticsApi = {
  getAnalytics: (id: number, params?: object) =>
    api.get(`/portfolios/${id}/analytics`, { params }).then(r => r.data),
  getRisk: (id: number, params?: object) =>
    api.get(`/portfolios/${id}/risk`, { params }).then(r => r.data),
  whatIf: (id: number, weights: Record<string, number>) =>
    api.post(`/portfolios/${id}/what-if`, { adjusted_weights: weights }).then(r => r.data),
}

export const marketApi = {
  refresh: () => api.post('/market-data/refresh').then(r => r.data),
  getPrices: (ticker: string) => api.get(`/market-data/${ticker}`).then(r => r.data),
}

export const signalsApi = {
  getSignals: () => api.get('/signals').then(r => r.data),
  getRegime: () => api.get('/signals/regime').then(r => r.data),
}

export const stressApi = {
  getScenarios: () => api.get('/stress-test/scenarios').then(r => r.data),
  run: (portfolioId: number, scenarioId: string) =>
    api.post(`/portfolios/${portfolioId}/stress-test`, { scenario_id: scenarioId }).then(r => r.data),
}

export const backtestApi = {
  create: (data: object) => api.post('/backtests', data).then(r => r.data),
  get: (runId: number) => api.get(`/backtests/${runId}`).then(r => r.data),
  list: (portfolioId: number) => api.get(`/portfolios/${portfolioId}/backtests`).then(r => r.data),
  precheck: (portfolioId: number, params?: object) =>
    api.get(`/portfolios/${portfolioId}/backtests/precheck`, { params }).then(r => r.data),
  listStrategies: () => api.get('/backtests/strategies').then(r => r.data),
  listBenchmarks: () => api.get('/backtests/benchmarks').then(r => r.data),
}
