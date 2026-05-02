import { create } from "zustand";
import { CITIES, DEFAULT_CITY, type CityId } from "./cities";

export type FlyTarget = {
  lng: number;
  lat: number;
  zoom: number;
  address: string;
};

export type SearchResult = {
  address: string;
  geoid: string;
  name: string;
  score: number;
  tier: string;
};

export type MapLayers = {
  heatmap: boolean;
  buildings: boolean;
  boundaries: boolean;
  glow: boolean;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
};

export type Persona = "insurer" | "resident" | "buyer" | "business" | "planner";
export type ViewMode = "verified" | "live" | "blended";
export type TimeRange = "7d" | "30d" | "90d" | "1y";

type AppState = {
  selectedTract: string | null;
  setSelectedTract: (id: string | null) => void;
  reportTract: string | null;
  setReportTract: (id: string | null) => void;
  flyTo: FlyTarget | null;
  setFlyTo: (target: FlyTarget | null) => void;
  searchResult: SearchResult | null;
  setSearchResult: (result: SearchResult | null) => void;
  tierFilter: Set<string>;
  setTierFilter: (tiers: Set<string>) => void;
  mapLayers: MapLayers;
  toggleMapLayer: (layer: keyof MapLayers) => void;
  chatOpen: boolean;
  setChatOpen: (open: boolean) => void;
  chatMessages: ChatMessage[];
  addChatMessage: (msg: ChatMessage) => void;
  clearChat: () => void;
  compareLeft: string | null;
  compareRight: string | null;
  setCompareLeft: (id: string | null) => void;
  setCompareRight: (id: string | null) => void;
  region: string;
  setRegion: (r: string) => void;
  city: CityId;
  setCity: (c: CityId) => void;
  authUser: { name: string; role: string } | null;
  setAuthUser: (u: { name: string; role: string } | null) => void;
  persona: Persona;
  setPersona: (p: Persona) => void;
  viewMode: ViewMode;
  setViewMode: (m: ViewMode) => void;
  timeRange: TimeRange;
  setTimeRange: (t: TimeRange) => void;
  provenanceOpen: boolean;
  setProvenanceOpen: (open: boolean) => void;
  watchlist: string[];
  addToWatchlist: (id: string) => void;
  removeFromWatchlist: (id: string) => void;
};

const ALL_TIERS = new Set(["Critical", "High", "Elevated", "Moderate", "Low"]);

export const useAppStore = create<AppState>((set) => ({
  selectedTract: null,
  setSelectedTract: (id) => set({ selectedTract: id }),
  reportTract: null,
  setReportTract: (id) => set({ reportTract: id }),
  flyTo: null,
  setFlyTo: (target) => set({ flyTo: target }),
  searchResult: null,
  setSearchResult: (result) => set({ searchResult: result }),
  tierFilter: ALL_TIERS,
  setTierFilter: (tiers) => set({ tierFilter: tiers }),
  mapLayers: { heatmap: true, buildings: true, boundaries: true, glow: true },
  toggleMapLayer: (layer) =>
    set((s) => ({ mapLayers: { ...s.mapLayers, [layer]: !s.mapLayers[layer] } })),
  chatOpen: false,
  setChatOpen: (open) => set({ chatOpen: open }),
  chatMessages: [],
  addChatMessage: (msg) =>
    set((s) => ({ chatMessages: [...s.chatMessages, msg] })),
  clearChat: () => set({ chatMessages: [] }),
  compareLeft: null,
  compareRight: null,
  setCompareLeft: (id) => set({ compareLeft: id }),
  setCompareRight: (id) => set({ compareRight: id }),
  region: DEFAULT_CITY,
  setRegion: (r) => set({ region: r }),
  city: DEFAULT_CITY,
  setCity: (c) => {
    const cfg = CITIES[c];
    set({
      city: c,
      region: c,
      selectedTract: null,
      reportTract: null,
      compareLeft: null,
      compareRight: null,
      searchResult: null,
      flyTo: cfg
        ? { lng: cfg.defaultCenter[0], lat: cfg.defaultCenter[1], zoom: cfg.defaultZoom, address: cfg.label }
        : null,
    });
  },
  authUser: null,
  setAuthUser: (u) => set({ authUser: u }),
  persona: "insurer",
  setPersona: (p) => set({ persona: p }),
  viewMode: "blended",
  setViewMode: (m) => set({ viewMode: m }),
  timeRange: "30d",
  setTimeRange: (t) => set({ timeRange: t }),
  provenanceOpen: false,
  setProvenanceOpen: (open) => set({ provenanceOpen: open }),
  watchlist: [],
  addToWatchlist: (id) =>
    set((s) => ({ watchlist: s.watchlist.includes(id) ? s.watchlist : [...s.watchlist, id] })),
  removeFromWatchlist: (id) =>
    set((s) => ({ watchlist: s.watchlist.filter((w) => w !== id) })),
}));
