/**
 * Per-city configuration that drives the map default view, the location
 * search behaviour, and copy throughout the UI.
 *
 * Mirrors the backend ``CITIES`` registry in ``app/core/data_store.py``.
 * Adding a new city requires updating both sides.
 */

export type CityId = "chicago" | "uk" | "uk_lsoa";

export type CityConfig = {
  id: CityId;
  /** Long display label, e.g. "CHICAGO, IL". */
  label: string;
  /** Short label for badges and selectors. */
  shortLabel: string;
  /** Country code for chrome/copy. */
  country: "US" | "UK";
  /** Geography unit shown in copy ("Tract" / "MSOA" / "Area"). */
  geographyUnit: string;
  /** Plural form for headers and totals. */
  geographyUnitPlural: string;
  /** Map default centre (lng, lat). */
  defaultCenter: [number, number];
  /** Map default zoom for the city overview. */
  defaultZoom: number;
  /** Map fly-to zoom when a search lands a point. */
  searchZoom: number;
  /** Bounding box for Nominatim search bias: lng_min,lat_min,lng_max,lat_max. */
  searchBbox: [number, number, number, number];
  /** Suffix appended to the user query before geocoding. */
  searchSuffix: string;
  /** Friendly scope label used in "Try a different address within ___". */
  scopeLabel: string;
  /** Default region id used when a route requires one and none is selected. */
  defaultRegionId: string;
  /** Copy used in the search "no region found" empty state. */
  searchEmptyMessage: string;
};

export const CITIES: Record<CityId, CityConfig> = {
  chicago: {
    id: "chicago",
    label: "CHICAGO, IL",
    shortLabel: "CHICAGO",
    country: "US",
    geographyUnit: "Tract",
    geographyUnitPlural: "Tracts",
    defaultCenter: [-87.635, 41.878],
    defaultZoom: 11.5,
    searchZoom: 14,
    searchBbox: [-88.0, 41.6, -87.3, 42.1],
    searchSuffix: ", Chicago",
    scopeLabel: "Chicago city limits",
    defaultRegionId: "17031839100",
    searchEmptyMessage: "NO TRACT DATA AVAILABLE FOR THIS LOCATION.",
  },
  uk: {
    id: "uk",
    label: "ENGLAND & WALES",
    shortLabel: "UK",
    country: "UK",
    geographyUnit: "MSOA",
    geographyUnitPlural: "MSOAs",
    defaultCenter: [-0.1276, 51.5074],
    defaultZoom: 9.8,
    searchZoom: 13,
    searchBbox: [-5.7, 49.9, 1.8, 55.8],
    searchSuffix: ", United Kingdom",
    scopeLabel: "England & Wales",
    defaultRegionId: "E02000001",
    searchEmptyMessage: "NO MSOA DATA AVAILABLE FOR THIS LOCATION.",
  },
  uk_lsoa: {
    id: "uk_lsoa",
    label: "ENGLAND & WALES (LSOA)",
    shortLabel: "UK·LSOA",
    country: "UK",
    geographyUnit: "LSOA",
    geographyUnitPlural: "LSOAs",
    defaultCenter: [-0.1276, 51.5074],
    defaultZoom: 11.0,
    searchZoom: 14,
    searchBbox: [-5.7, 49.9, 1.8, 55.8],
    searchSuffix: ", United Kingdom",
    scopeLabel: "England & Wales (LSOA)",
    defaultRegionId: "E01000001",
    searchEmptyMessage: "NO LSOA DATA AVAILABLE FOR THIS LOCATION.",
  },
};

export const DEFAULT_CITY: CityId = "uk";

export function getCity(id: string | null | undefined): CityConfig {
  if (!id) return CITIES[DEFAULT_CITY];
  return (CITIES as Record<string, CityConfig>)[id] ?? CITIES[DEFAULT_CITY];
}

export const ALL_CITIES: CityConfig[] = Object.values(CITIES);
