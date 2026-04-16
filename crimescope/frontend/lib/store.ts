import { create } from "zustand";

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
  authUser: { name: string; role: string } | null;
  setAuthUser: (u: { name: string; role: string } | null) => void;
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
  region: "chicago",
  setRegion: (r) => set({ region: r }),
  authUser: null,
  setAuthUser: (u) => set({ authUser: u }),
}));
