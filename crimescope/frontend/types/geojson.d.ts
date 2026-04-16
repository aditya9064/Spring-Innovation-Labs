declare namespace GeoJSON {
  interface FeatureCollection {
    type: "FeatureCollection";
    features: Feature[];
  }
  interface Feature {
    type: "Feature";
    geometry: Geometry;
    properties: Record<string, unknown>;
  }
  type Geometry =
    | { type: "Point"; coordinates: number[] }
    | { type: "MultiPoint"; coordinates: number[][] }
    | { type: "LineString"; coordinates: number[][] }
    | { type: "MultiLineString"; coordinates: number[][][] }
    | { type: "Polygon"; coordinates: number[][][] }
    | { type: "MultiPolygon"; coordinates: number[][][][] }
    | { type: "GeometryCollection"; geometries: Geometry[] };
}
