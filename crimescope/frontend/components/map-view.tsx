"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import { useAppStore } from "../lib/store";
import { fetchGeoJSON } from "../lib/api";
import { getCity } from "../lib/cities";

const TIER_COLORS: Record<string, string> = {
  Critical: "#ef4444",
  High: "#f97316",
  Elevated: "#eab308",
  Moderate: "#3b82f6",
  Low: "#22c55e",
};

function pointInPolygon(
  point: [number, number],
  ring: number[][],
): boolean {
  let inside = false;
  const [px, py] = point;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if ((yi > py) !== (yj > py) && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

function pointInFeature(
  point: [number, number],
  feature: GeoJSON.Feature,
): boolean {
  const g = feature.geometry;
  if (g.type === "Polygon") {
    return pointInPolygon(point, g.coordinates[0]);
  }
  if (g.type === "MultiPolygon") {
    return g.coordinates.some((poly) => pointInPolygon(point, poly[0]));
  }
  return false;
}

function ringCentroid(ring: number[][]): [number, number] {
  let sx = 0,
    sy = 0;
  for (const [x, y] of ring) {
    sx += x;
    sy += y;
  }
  return [sx / ring.length, sy / ring.length];
}

function getCentroid(feature: GeoJSON.Feature): [number, number] | null {
  const g = feature.geometry;
  if (g.type === "Polygon") return ringCentroid(g.coordinates[0]);
  if (g.type === "MultiPolygon") {
    let best = g.coordinates[0][0];
    for (const poly of g.coordinates) {
      if (poly[0].length > best.length) best = poly[0];
    }
    return ringCentroid(best);
  }
  return null;
}

function buildPointsFC(geojson: GeoJSON.FeatureCollection): GeoJSON.FeatureCollection {
  const points: GeoJSON.Feature[] = [];
  for (const f of geojson.features) {
    const c = getCentroid(f);
    if (!c) continue;
    const score = (f.properties?.risk_score as number) ?? 0;
    points.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: c },
      properties: f.properties,
    });
    if (score > 40) {
      const count = Math.floor(score / 15);
      for (let i = 0; i < count; i++) {
        const jitter = 0.003;
        points.push({
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [c[0] + (Math.random() - 0.5) * jitter, c[1] + (Math.random() - 0.5) * jitter],
          },
          properties: { ...f.properties },
        });
      }
    }
  }
  return { type: "FeatureCollection", features: points };
}

export default function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const geojsonRef = useRef<GeoJSON.FeatureCollection | null>(null);
  const searchMarkerRef = useRef<maplibregl.Marker | null>(null);
  const setSelectedTract = useAppStore((s) => s.setSelectedTract);
  const initialCity = useAppStore.getState().city;
  const initialCfg = getCity(initialCity);

  function clearSearchHighlight(m: maplibregl.Map | null) {
    if (searchMarkerRef.current) {
      searchMarkerRef.current.remove();
      searchMarkerRef.current = null;
    }
    if (!m) return;
    try {
      if (m.getLayer("tracts-search-highlight"))
        m.setFilter("tracts-search-highlight", ["==", "tract_geoid", ""]);
      if (m.getLayer("tracts-search-highlight-glow"))
        m.setFilter("tracts-search-highlight-glow", ["==", "tract_geoid", ""]);
    } catch { /* layer may not exist yet */ }
  }

  function dropSearchPin(m: maplibregl.Map, lng: number, lat: number) {
    if (searchMarkerRef.current) {
      searchMarkerRef.current.remove();
      searchMarkerRef.current = null;
    }
    const el = document.createElement("div");
    el.className = "cs-search-pin";
    el.innerHTML =
      '<div class="cs-search-pin-pulse"></div><div class="cs-search-pin-dot"></div>';
    searchMarkerRef.current = new maplibregl.Marker({ element: el, anchor: "center" })
      .setLngLat([lng, lat])
      .addTo(m);
  }

  // Layer toggle subscription
  useEffect(() => {
    const unsub = useAppStore.subscribe((state, prev) => {
      const m = mapRef.current;
      if (!m || state.mapLayers === prev.mapLayers) return;
      const layers = state.mapLayers;

      const setVis = (id: string, visible: boolean) => {
        try {
          if (m.getLayer(id))
            m.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
        } catch { /* layer may not exist */ }
      };

      setVis("crime-heatmap", layers.heatmap);
      setVis("3d-buildings", layers.buildings);
      setVis("building-edges", layers.buildings);
      setVis("tracts-border-glow", layers.boundaries);
      setVis("tracts-line", layers.boundaries);
      setVis("crime-glow-outer", layers.glow);
      setVis("crime-glow-inner", layers.glow);
      setVis("crime-core", layers.glow);
    });
    return unsub;
  }, []);

  // Watch for city changes — re-fetch the city's GeoJSON and swap source data
  useEffect(() => {
    const unsub = useAppStore.subscribe((state, prev) => {
      if (state.city === prev.city) return;
      const m = mapRef.current;
      if (!m) return;
      fetchGeoJSON(state.city)
        .then((geojson) => {
          geojsonRef.current = geojson;
          const tractSrc = m.getSource("tracts") as maplibregl.GeoJSONSource | undefined;
          if (tractSrc) tractSrc.setData(geojson);
          const pointsSrc = m.getSource("crime-points") as maplibregl.GeoJSONSource | undefined;
          if (pointsSrc) pointsSrc.setData(buildPointsFC(geojson));
        })
        .catch((err) => console.error("[MapView] city switch geojson load failed", err));
    });
    return unsub;
  }, []);

  // Watch for searchResult changes — apply polygon highlight, clear pin on clear
  useEffect(() => {
    const unsub = useAppStore.subscribe((state, prev) => {
      if (state.searchResult === prev.searchResult) return;
      const m = mapRef.current;
      if (!m) return;
      if (state.searchResult) {
        try {
          if (m.getLayer("tracts-search-highlight"))
            m.setFilter("tracts-search-highlight", [
              "==",
              "tract_geoid",
              state.searchResult.geoid,
            ]);
          if (m.getLayer("tracts-search-highlight-glow"))
            m.setFilter("tracts-search-highlight-glow", [
              "==",
              "tract_geoid",
              state.searchResult.geoid,
            ]);
        } catch { /* layers may still be loading */ }
      } else {
        clearSearchHighlight(m);
      }
    });
    return unsub;
  }, []);

  // Watch for flyTo requests from the store
  useEffect(() => {
    const unsub = useAppStore.subscribe((state, prev) => {
      if (!state.flyTo || state.flyTo === prev.flyTo) return;
      const m = mapRef.current;
      if (!m) return;

      const { lng, lat, zoom, address } = state.flyTo;
      const FLY_DURATION = 3000;
      // City-overview flights pass zoom ≤ 12; address searches pass ~14.
      const isOverview = zoom <= 12;

      m.flyTo({
        center: [lng, lat],
        zoom,
        pitch: isOverview ? 45 : 72,
        bearing: isOverview ? 0 : m.getBearing() + 20,
        duration: FLY_DURATION,
        essential: true,
      });

      // Skip point-in-polygon tract resolution for city-overview flights —
      // we don't have a meaningful "address" to resolve and the geojson may
      // still be loading.
      if (isOverview) {
        clearSearchHighlight(m);
        useAppStore.getState().setFlyTo(null);
        return;
      }

      dropSearchPin(m, lng, lat);

      function findTractAtPoint(retries = 5) {
        const map = mapRef.current;
        let found = false;
        const gc = geojsonRef.current;

        if (!gc && retries > 0) {
          setTimeout(() => findTractAtPoint(retries - 1), 1000);
          return;
        }

        if (gc) {
          for (const f of gc.features) {
            if (pointInFeature([lng, lat], f)) {
              const p = f.properties!;
              setSelectedTract(p.tract_geoid as string);
              useAppStore.getState().setSearchResult({
                address,
                geoid: p.tract_geoid as string,
                name: (p.name as string) || `Tract ${(p.tract_geoid as string).slice(-6)}`,
                score: p.risk_score as number,
                tier: p.risk_tier as string,
              });
              found = true;
              break;
            }
          }
        }

        if (!found && map) {
          try {
            if (map.getLayer("tracts-interact")) {
              const screenPt = map.project([lng, lat]);
              const hits = map.queryRenderedFeatures(screenPt, {
                layers: ["tracts-interact"],
              });
              if (hits.length > 0) {
                const p = hits[0].properties!;
                setSelectedTract(p.tract_geoid as string);
                useAppStore.getState().setSearchResult({
                  address,
                  geoid: p.tract_geoid as string,
                  name: (p.name as string) || `Tract ${(p.tract_geoid as string).slice(-6)}`,
                  score: p.risk_score as number,
                  tier: p.risk_tier as string,
                });
                found = true;
              }
            }
          } catch {
            /* layer may not exist yet */
          }
        }

        if (!found) {
          useAppStore.getState().setSearchResult(null);
          const cb = (window as unknown as Record<string, unknown>).__csOnNoTract;
          if (typeof cb === "function") cb();
        }

        useAppStore.getState().setFlyTo(null);
      }

      setTimeout(findTractAtPoint, FLY_DURATION + 300);
    });
    return unsub;
  }, [setSelectedTract]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const m = new maplibregl.Map({
      container: containerRef.current,
      style:
        "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: initialCfg.defaultCenter,
      zoom: initialCfg.defaultZoom,
      pitch: 60,
      bearing: -20,
      maxPitch: 85,
      antialias: true,
    });
    mapRef.current = m;

    m.addControl(
      new maplibregl.NavigationControl({ visualizePitch: true }),
      "top-left",
    );

    m.on("load", () => {
      if (mapRef.current !== m) return;

      try {
      const style = m.getStyle();
      if (!style?.layers) return;

      // --- Atmospheric fog for depth ---
      const setFog = (m as unknown as Record<string, (...args: unknown[]) => void>).setFog;
      if (typeof setFog === "function") {
        setFog.call(m, {
          range: [0.5, 10],
          color: "rgba(10, 10, 20, 1)",
          "horizon-blend": 0.08,
          "high-color": "rgba(20, 20, 40, 1)",
          "space-color": "rgba(5, 5, 15, 1)",
          "star-intensity": 0.15,
        });
      }

      // --- Darken road/label layers for cinematic feel ---
      for (const layer of style.layers) {
        if (layer.type === "line" && layer.id.includes("road")) {
          try { m.setPaintProperty(layer.id, "line-opacity", 0.4); } catch { /* */ }
        }
        if (layer.type === "symbol" && !layer.id.includes("place")) {
          try { m.setLayoutProperty(layer.id, "visibility", "none"); } catch { /* */ }
        }
      }

      // --- 3D buildings: tall, detailed, atmospheric ---
      let bldgSource = "";
      let bldgSourceLayer = "";
      const removals: string[] = [];

      for (const layer of style.layers) {
        const sl = (layer as Record<string, unknown>)["source-layer"];
        if (
          typeof sl === "string" &&
          (sl === "building" || layer.id.toLowerCase().includes("building"))
        ) {
          bldgSource = (layer as Record<string, unknown>).source as string;
          bldgSourceLayer = sl;
          removals.push(layer.id);
        }
      }

      for (const id of removals) {
        try { m.removeLayer(id); } catch { /* */ }
      }

      if (bldgSource) {
        m.addLayer({
          id: "3d-buildings",
          source: bldgSource,
          "source-layer": bldgSourceLayer,
          type: "fill-extrusion",
          minzoom: 12,
          paint: {
            "fill-extrusion-color": [
              "interpolate", ["linear"], ["zoom"],
              12, "#080a0e",
              15, "#0c1018",
              17, "#141a24",
            ],
            "fill-extrusion-height": [
              "interpolate", ["linear"], ["zoom"],
              12, 0,
              13.5, ["coalesce", ["get", "render_height"], 12],
            ],
            "fill-extrusion-base": [
              "coalesce", ["get", "render_min_height"], 0,
            ],
            "fill-extrusion-opacity": [
              "interpolate", ["linear"], ["zoom"],
              12, 0.3,
              14, 0.85,
              17, 0.95,
            ],
          },
        });

        // Building edge glow — gives structure outline at night
        m.addLayer({
          id: "building-edges",
          source: bldgSource,
          "source-layer": bldgSourceLayer,
          type: "line",
          minzoom: 14,
          paint: {
            "line-color": "rgba(100, 140, 200, 0.06)",
            "line-width": [
              "interpolate", ["linear"], ["zoom"],
              14, 0.3,
              17, 0.8,
            ],
          },
        });
      }

      // --- Load crime data for the currently selected city ---
      fetchGeoJSON(useAppStore.getState().city)
        .then((geojson) => {
          if (m.getSource("tracts")) return;

          geojsonRef.current = geojson;
          m.addSource("tracts", { type: "geojson", data: geojson });

          const pointsFC = buildPointsFC(geojson);
          m.addSource("crime-points", { type: "geojson", data: pointsFC });

          const below3D = m.getLayer("3d-buildings") ? "3d-buildings" : undefined;

          // --- Ground-plane heatmap: visible beneath buildings ---
          m.addLayer({
            id: "crime-heatmap",
            type: "heatmap",
            source: "crime-points",
            maxzoom: 18,
            paint: {
              "heatmap-weight": [
                "interpolate", ["linear"], ["get", "risk_score"],
                0, 0,
                25, 0.12,
                50, 0.4,
                75, 0.75,
                100, 1,
              ],
              "heatmap-intensity": [
                "interpolate", ["linear"], ["zoom"],
                10, 0.6,
                14, 2.5,
                17, 4,
              ],
              "heatmap-radius": [
                "interpolate", ["linear"], ["zoom"],
                10, 15,
                13, 40,
                15, 70,
                17, 100,
              ],
              "heatmap-color": [
                "interpolate", ["linear"], ["heatmap-density"],
                0,    "rgba(0,0,0,0)",
                0.05, "rgba(10,20,60,0.25)",
                0.15, "rgba(30,58,138,0.45)",
                0.3,  "rgba(59,130,246,0.55)",
                0.45, "rgba(124,58,237,0.6)",
                0.6,  "rgba(245,158,11,0.7)",
                0.75, "rgba(249,115,22,0.82)",
                0.88, "rgba(239,68,68,0.92)",
                1,    "rgba(185,28,28,1)",
              ],
              "heatmap-opacity": [
                "interpolate", ["linear"], ["zoom"],
                10, 0.85,
                15, 0.7,
                17, 0.55,
              ],
            },
          }, below3D);

          // --- Street-level glow spots: neon puddles on the ground ---
          m.addLayer({
            id: "crime-glow-outer",
            type: "circle",
            source: "crime-points",
            minzoom: 13,
            paint: {
              "circle-radius": [
                "interpolate", ["linear"], ["zoom"],
                13, ["interpolate", ["linear"], ["get", "risk_score"], 0, 3, 100, 18],
                16, ["interpolate", ["linear"], ["get", "risk_score"], 0, 10, 100, 55],
                18, ["interpolate", ["linear"], ["get", "risk_score"], 0, 20, 100, 90],
              ],
              "circle-color": [
                "match", ["get", "risk_tier"],
                "Critical", "rgba(239,68,68,0.12)",
                "High", "rgba(249,115,22,0.10)",
                "Elevated", "rgba(234,179,8,0.08)",
                "Moderate", "rgba(59,130,246,0.06)",
                "Low", "rgba(34,197,94,0.04)",
                "rgba(100,116,139,0.04)",
              ],
              "circle-blur": 1.2,
            },
          }, below3D);

          m.addLayer({
            id: "crime-glow-inner",
            type: "circle",
            source: "crime-points",
            minzoom: 14,
            paint: {
              "circle-radius": [
                "interpolate", ["linear"], ["zoom"],
                14, ["interpolate", ["linear"], ["get", "risk_score"], 0, 1, 100, 6],
                16, ["interpolate", ["linear"], ["get", "risk_score"], 0, 3, 100, 18],
                18, ["interpolate", ["linear"], ["get", "risk_score"], 0, 6, 100, 30],
              ],
              "circle-color": [
                "match", ["get", "risk_tier"],
                "Critical", "rgba(239,68,68,0.35)",
                "High", "rgba(249,115,22,0.28)",
                "Elevated", "rgba(234,179,8,0.22)",
                "Moderate", "rgba(59,130,246,0.15)",
                "Low", "rgba(34,197,94,0.10)",
                "rgba(100,116,139,0.08)",
              ],
              "circle-blur": 0.6,
            },
          }, below3D);

          // --- Bright crime hotspot core at street level ---
          m.addLayer({
            id: "crime-core",
            type: "circle",
            source: "crime-points",
            minzoom: 15,
            filter: [">", ["get", "risk_score"], 55],
            paint: {
              "circle-radius": [
                "interpolate", ["linear"], ["zoom"],
                15, 2,
                17, 5,
                18, 8,
              ],
              "circle-color": [
                "match", ["get", "risk_tier"],
                "Critical", "#ef4444",
                "High", "#f97316",
                "Elevated", "#eab308",
                "#3b82f6",
              ],
              "circle-opacity": [
                "interpolate", ["linear"], ["zoom"],
                15, 0.4,
                17, 0.7,
              ],
              "circle-blur": 0.3,
            },
          });

          // --- Tract boundary glow on ground (subtle colored borders) ---
          m.addLayer({
            id: "tracts-border-glow",
            type: "line",
            source: "tracts",
            paint: {
              "line-color": [
                "match", ["get", "risk_tier"],
                "Critical", "rgba(239,68,68,0.25)",
                "High", "rgba(249,115,22,0.18)",
                "Elevated", "rgba(234,179,8,0.12)",
                "Moderate", "rgba(59,130,246,0.08)",
                "Low", "rgba(34,197,94,0.05)",
                "rgba(100,116,139,0.05)",
              ],
              "line-width": [
                "interpolate", ["linear"], ["zoom"],
                11, 0.5,
                14, 1.5,
                17, 3,
              ],
              "line-blur": [
                "interpolate", ["linear"], ["zoom"],
                11, 1,
                14, 2,
                17, 4,
              ],
            },
          });

          m.addLayer({
            id: "tracts-line",
            type: "line",
            source: "tracts",
            paint: {
              "line-color": "rgba(255,255,255,0.05)",
              "line-width": 0.5,
            },
          });

          // Hover highlight
          m.addLayer({
            id: "tracts-hover",
            type: "line",
            source: "tracts",
            paint: { "line-color": "#ffffff", "line-width": 2.5 },
            filter: ["==", "tract_geoid", ""],
          });

          // Search highlight — bright cyan border + glow on the resolved region
          m.addLayer({
            id: "tracts-search-highlight-glow",
            type: "line",
            source: "tracts",
            paint: {
              "line-color": "#22d3ee",
              "line-width": [
                "interpolate", ["linear"], ["zoom"],
                10, 4,
                14, 8,
                17, 14,
              ],
              "line-blur": [
                "interpolate", ["linear"], ["zoom"],
                10, 2,
                14, 4,
                17, 8,
              ],
              "line-opacity": 0.55,
            },
            filter: ["==", "tract_geoid", ""],
          });
          m.addLayer({
            id: "tracts-search-highlight",
            type: "line",
            source: "tracts",
            paint: {
              "line-color": "#22d3ee",
              "line-width": [
                "interpolate", ["linear"], ["zoom"],
                10, 1.5,
                14, 3,
                17, 4.5,
              ],
              "line-opacity": 1,
            },
            filter: ["==", "tract_geoid", ""],
          });

          // Invisible interaction layer
          m.addLayer({
            id: "tracts-interact",
            type: "fill",
            source: "tracts",
            paint: {
              "fill-color": "#000000",
              "fill-opacity": 0.01,
            },
          });

          // --- Popup ---
          const popup = new maplibregl.Popup({
            closeButton: false,
            closeOnClick: false,
            className: "crimescope-popup",
            offset: 14,
          });

          m.on("mousemove", "tracts-interact", (e) => {
            m.getCanvas().style.cursor = "pointer";
            const f = e.features?.[0];
            if (!f) return;
            const p = f.properties!;
            m.setFilter("tracts-hover", ["==", "tract_geoid", p.tract_geoid]);
            const tc = TIER_COLORS[p.risk_tier as string] || "#64748b";
            const score = Number(p.risk_score);
            const barW = Math.max(score, 5);
            popup
              .setLngLat(e.lngLat)
              .setHTML(
                `<div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#e2e8f0;background:rgba(5,5,12,0.96);padding:12px 16px;border:1px solid ${tc}33;min-width:200px;backdrop-filter:blur(8px);box-shadow:0 8px 32px rgba(0,0,0,0.6)">
                  <div style="font-weight:700;font-size:12px;margin-bottom:6px;letter-spacing:0.3px">${p.name || p.tract_geoid}</div>
                  <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:8px">
                    <span style="color:${tc};font-weight:800;font-size:20px">${p.risk_score}</span>
                    <span style="color:#334155;font-size:9px">/ 100</span>
                  </div>
                  <div style="height:3px;background:#1a1a2e;border-radius:2px;margin-bottom:8px;overflow:hidden">
                    <div style="height:100%;width:${barW}%;background:${tc};border-radius:2px"></div>
                  </div>
                  <span style="display:inline-block;padding:3px 8px;font-size:9px;font-weight:700;background:${tc}18;color:${tc};border:1px solid ${tc}33;text-transform:uppercase;letter-spacing:0.8px">${p.risk_tier}</span>
                </div>`,
              )
              .addTo(m);
          });

          m.on("mouseleave", "tracts-interact", () => {
            m.getCanvas().style.cursor = "";
            m.setFilter("tracts-hover", ["==", "tract_geoid", ""]);
            popup.remove();
          });

          const clickPopup = new maplibregl.Popup({
            closeButton: true,
            closeOnClick: true,
            className: "crimescope-click-popup",
            offset: 18,
            maxWidth: "280px",
          });

          m.on("click", "tracts-interact", (e) => {
            const f = e.features?.[0];
            if (!f) return;
            const p = f.properties!;
            const geoid = p.tract_geoid as string;
            setSelectedTract(geoid);

            popup.remove();

            const score = Number(p.risk_score) || 0;
            const tier = (p.risk_tier as string) || "Unknown";
            const tc = TIER_COLORS[tier] || "#64748b";
            const violent = Number(p.violent_score) || 0;
            const property = Number(p.property_score) || 0;
            const other = Math.max(0, score - violent - property);

            const total = violent + property + other || 1;
            const pctV = Math.round((violent / total) * 100);
            const pctP = Math.round((property / total) * 100);
            const pctO = 100 - pctV - pctP;

            const dominant = pctP >= pctV ? "property" : "violent";
            const insight = `Risk is driven primarily by high ${dominant} crime relative to neighboring regions.`;

            const name = (p.name as string) || `Tract ${geoid.slice(-6)}`;

            clickPopup
              .setLngLat(e.lngLat)
              .setHTML(
                `<div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#e2e8f0;background:rgba(5,5,12,0.97);padding:14px 16px;border:1px solid ${tc}55;min-width:230px;backdrop-filter:blur(12px);box-shadow:0 12px 40px rgba(0,0,0,0.7)">
                  <div style="font-weight:700;font-size:13px;margin-bottom:8px;letter-spacing:0.3px">${name}</div>

                  <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:4px">
                    <span style="font-size:9px;color:#94a3b8;font-weight:600;letter-spacing:0.5px">RISK SCORE</span>
                  </div>
                  <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:6px">
                    <span style="color:${tc};font-weight:800;font-size:26px;line-height:1">${score}</span>
                    <span style="color:#475569;font-size:11px">/ 100</span>
                    <span style="padding:2px 7px;font-size:8px;font-weight:700;background:${tc}20;color:${tc};border:1px solid ${tc}40;text-transform:uppercase;letter-spacing:0.8px;margin-left:auto">${tier}</span>
                  </div>

                  <div style="height:4px;background:#1e293b;border-radius:2px;margin-bottom:12px;overflow:hidden">
                    <div style="height:100%;width:${Math.max(score, 3)}%;background:${tc};border-radius:2px"></div>
                  </div>

                  <div style="font-size:9px;color:#94a3b8;font-weight:600;letter-spacing:0.5px;margin-bottom:6px">BREAKDOWN</div>
                  <div style="display:flex;flex-direction:column;gap:4px;margin-bottom:12px">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                      <span style="color:#cbd5e1">Property crime</span>
                      <span style="font-weight:700;color:#f97316">${pctP}%</span>
                    </div>
                    <div style="height:3px;background:#1e293b;border-radius:2px;overflow:hidden">
                      <div style="height:100%;width:${pctP}%;background:#f97316;border-radius:2px"></div>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center">
                      <span style="color:#cbd5e1">Violent crime</span>
                      <span style="font-weight:700;color:#ef4444">${pctV}%</span>
                    </div>
                    <div style="height:3px;background:#1e293b;border-radius:2px;overflow:hidden">
                      <div style="height:100%;width:${pctV}%;background:#ef4444;border-radius:2px"></div>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center">
                      <span style="color:#cbd5e1">Other</span>
                      <span style="font-weight:700;color:#64748b">${pctO}%</span>
                    </div>
                    <div style="height:3px;background:#1e293b;border-radius:2px;overflow:hidden">
                      <div style="height:100%;width:${pctO}%;background:#64748b;border-radius:2px"></div>
                    </div>
                  </div>

                  <div style="padding:8px 10px;background:rgba(59,130,246,0.08);border-left:2px solid #3b82f6;font-size:10px;color:#93c5fd;line-height:1.5;font-style:italic">${insight}</div>
                </div>`,
              )
              .addTo(m);
          });
        })
        .catch(console.error);
      } catch (err) {
        console.error("[CrimeScope] load handler error:", err);
      }
    });

    return () => {
      mapRef.current = null;
      m.remove();
    };
  }, [setSelectedTract]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}
