import { create } from 'zustand'

type ThemeMode = 'light' | 'dark'

interface AppState {
  selectedPortfolioId: number | null
  setSelectedPortfolio: (id: number) => void
  whatIfWeights: Record<string, number>
  setWhatIfWeight: (ticker: string, weight: number) => void
  resetWhatIf: () => void
  isOnline: boolean
  setOnline: (v: boolean) => void
  theme: ThemeMode
  setTheme: (theme: ThemeMode) => void
  toggleTheme: () => void
}

const defaultTheme: ThemeMode =
  typeof window !== 'undefined' && window.localStorage.getItem('theme') === 'light'
    ? 'light'
    : 'dark'

export const useAppStore = create<AppState>((set) => ({
  selectedPortfolioId: null,
  setSelectedPortfolio: (id) => set({ selectedPortfolioId: id }),
  whatIfWeights: {},
  setWhatIfWeight: (ticker, weight) =>
  set((s) => ({ whatIfWeights: { ...s.whatIfWeights, [ticker]: weight } })),
  resetWhatIf: () => set({ whatIfWeights: {} }),
  isOnline: true,
  setOnline: (v) => set({ isOnline: v }),
  theme: defaultTheme,
  setTheme: (theme) => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('theme', theme)
    }
    set({ theme })
  },
  toggleTheme: () =>
    set((state) => {
      const next = state.theme === 'dark' ? 'light' : 'dark'
      if (typeof window !== 'undefined') {
        window.localStorage.setItem('theme', next)
      }
      return { theme: next }
    }),
}))
