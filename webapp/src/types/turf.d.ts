declare module '@turf/turf' {
  import type { Feature, Point, LineString, Position } from 'geojson';

  export function point(coordinates: Position): Feature<Point>;
  export function lineString(coordinates: Position[]): Feature<LineString>;
  export function distance(from: Feature<Point>, to: Feature<Point>, options?: { units?: string }): number;
  export function length(line: Feature<LineString>, options?: { units?: string }): number;
  export function midpoint(point1: Feature<Point>, point2: Feature<Point>): Feature<Point>;
  export function simplify(feature: Feature<LineString>, options?: { tolerance?: number }): Feature<LineString>;
}
