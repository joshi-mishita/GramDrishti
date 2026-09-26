import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  Map as MapLibreMap,
  NavigationControl,
  setWorkerUrl,
  type GeoJSONSourceSpecification,
  type MapLayerMouseEvent,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre 6 loads its worker from next to its own module. The production build does not
// keep that file, so Vite bundles the worker and MapLibre gets its URL. In dev, MapLibre is
// excluded from pre-bundling (vite.config.ts) and finds the original file itself.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import type { BlockCollection, PanchayatCollection } from "../../api/types";
import { fillColorExpression, type Ramp } from "../../lib/ramps";
import { boundsOf } from "./mapData";

interface Props {
  panchayats: PanchayatCollection;
  blocks: BlockCollection | undefined;
  /** Painted value per panchayat_id; ids not in the map are drawn as "no value". */
  values: ReadonlyMap<string, number | null>;
  ramp: Ramp | null;
  selectedPid: string | null;
  onSelect: (pid: string) => void;
  renderTooltip: (pid: string) => ReactNode;
  /** Accessible name of the map region. */
  label: string;
  /** Shown instead of the map when the browser cannot draw it (no WebGL). */
  fallback: ReactNode;
  /** Changes whenever the painted data changes; exposed as data-painted once drawn. */
  paintKey: string;
}

interface Hover {
  pid: string;
  /** CSS transform that places the tooltip next to the pointer. */
  transform: string;
}

/** Room around the district for the zoom buttons (right) and the legend (bottom). */
const FIT_PADDING = { top: 24, right: 56, bottom: 140, left: 24 };

const GP = "gp";
const BLK = "blk";

/** Reads a design token; MapLibre paint properties need literal colours. */
function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Places the tooltip below-right of the pointer, flipped left or up near the edges. */
function tooltipTransform(x: number, y: number, box: HTMLElement): string {
  const tx = x > box.clientWidth - 240 ? `calc(${x - 14}px - 100%)` : `${x + 14}px`;
  const ty = y > box.clientHeight - 120 ? `calc(${y - 14}px - 100%)` : `${y + 14}px`;
  return `translate(${tx}, ${ty})`;
}

/**
 * Panchayat polygons coloured by feature-state (Guide 8.1). Sources and layers are added
 * once; new values only call setFeatureState, and a new ramp only sets the fill paint, so
 * switching view mode never refetches or rebuilds anything.
 */
export function MapView({
  panchayats,
  blocks,
  values,
  ramp,
  selectedPid,
  onSelect,
  renderTooltip,
  label,
  fallback,
  paintKey,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // The map instance once its style has loaded. Effects use this, never a map that is still
  // loading, so they cannot race map creation.
  const [readyMap, setReadyMap] = useState<MapLibreMap | null>(null);
  const [failed, setFailed] = useState(false);
  const [hover, setHover] = useState<Hover | null>(null);
  const [painted, setPainted] = useState<string | null>(null);
  const onSelectRef = useRef(onSelect);
  const shownSelected = useRef<string | null>(null);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  // Create the map once per Panchayat boundary set (the geo query never goes stale).
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const bounds = boundsOf(panchayats);
    if (import.meta.env.PROD) setWorkerUrl(workerUrl);
    let map: MapLibreMap;
    try {
      map = new MapLibreMap({
        container,
        style: {
          version: 8,
          sources: {},
          layers: [
            { id: "bg", type: "background", paint: { "background-color": token("--canvas") } },
          ],
        },
        bounds: bounds ?? undefined,
        fitBoundsOptions: { padding: FIT_PADDING },
        attributionControl: false,
        dragRotate: false,
        pitchWithRotate: false,
        touchPitch: false,
      });
    } catch {
      // No WebGL (old phone, disabled GPU): show the fallback; the table still works.
      // Deferred so the state change happens after this effect, not inside it.
      queueMicrotask(() => setFailed(true));
      return;
    }
    map.touchZoomRotate.disableRotation();
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");

    map.on("load", () => {
      map.addSource(GP, {
        type: "geojson",
        // The contract type has the same GeoJSON shape; MapLibre wants its own type.
        data: panchayats as unknown as GeoJSONSourceSpecification["data"],
        promoteId: "panchayat_id",
      });
      map.addLayer({
        id: "gp-fill",
        type: "fill",
        source: GP,
        paint: { "fill-color": token("--skeleton"), "fill-opacity": 0.9 },
      });
      map.addLayer({
        id: "gp-line",
        type: "line",
        source: GP,
        paint: { "line-color": token("--surface"), "line-width": 0.6 },
      });
      // Hover and selection outlines; block lines are inserted below them when they load.
      map.addLayer({
        id: "gp-hover",
        type: "line",
        source: GP,
        paint: {
          "line-color": token("--ink"),
          "line-width": ["case", ["boolean", ["feature-state", "hover"], false], 1.5, 0],
        },
      });
      map.addLayer({
        id: "gp-selected",
        type: "line",
        source: GP,
        paint: {
          "line-color": token("--ink"),
          "line-width": ["case", ["boolean", ["feature-state", "selected"], false], 3, 0],
        },
      });
      setReadyMap(map);
    });

    let hovered: string | null = null;
    const setHovered = (pid: string | null) => {
      if (hovered === pid) return;
      if (hovered) map.setFeatureState({ source: GP, id: hovered }, { hover: false });
      if (pid) map.setFeatureState({ source: GP, id: pid }, { hover: true });
      hovered = pid;
    };
    map.on("mousemove", "gp-fill", (e: MapLayerMouseEvent) => {
      const id = e.features?.[0]?.id;
      if (typeof id !== "string") return;
      setHovered(id);
      setHover({ pid: id, transform: tooltipTransform(e.point.x, e.point.y, container) });
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "gp-fill", () => {
      setHovered(null);
      setHover(null);
      map.getCanvas().style.cursor = "";
    });
    map.on("click", "gp-fill", (e: MapLayerMouseEvent) => {
      const id = e.features?.[0]?.id;
      if (typeof id === "string") onSelectRef.current(id);
    });

    // The container changes size when the panel opens or the table hides the map. Until
    // the user pans or zooms, keep the whole district in view at every size.
    let userMoved = false;
    map.on("movestart", (e: { originalEvent?: unknown }) => {
      if (e.originalEvent) userMoved = true;
    });
    const observer = new ResizeObserver(() => {
      map.resize();
      if (!userMoved && bounds && container.clientHeight > 0) {
        map.fitBounds(bounds, { padding: FIT_PADDING, animate: false });
      }
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      map.remove();
      shownSelected.current = null;
      setReadyMap(null);
    };
  }, [panchayats]);

  // Block outlines: added once, whenever both the map and the block boundaries are ready.
  useEffect(() => {
    const map = readyMap;
    if (!map || !blocks || map.getSource(BLK)) return;
    map.addSource(BLK, {
      type: "geojson",
      data: blocks as unknown as GeoJSONSourceSpecification["data"],
    });
    map.addLayer(
      {
        id: "blk-line",
        type: "line",
        source: BLK,
        paint: { "line-color": token("--ink"), "line-width": 1.6 },
      },
      "gp-hover",
    );
  }, [readyMap, blocks]);

  // Ramp change: one paint property update.
  useEffect(() => {
    const map = readyMap;
    if (!map) return;
    const color = ramp ? fillColorExpression(ramp, token("--skeleton")) : token("--skeleton");
    // The expression is built from our typed ramp config; MapLibre validates it at runtime.
    map.setPaintProperty("gp-fill", "fill-color", color as never);
  }, [ramp, readyMap]);

  // Value change: one setFeatureState per Panchayat, no layer or source change.
  useEffect(() => {
    const map = readyMap;
    if (!map) return;
    for (const f of panchayats.features) {
      const id = f.properties.panchayat_id;
      map.setFeatureState({ source: GP, id }, { v: values.get(id) ?? null });
    }
    // Screenshots and tests wait for data-painted to match the current paintKey.
    map.once("idle", () => setPainted(paintKey));
    map.triggerRepaint();
  }, [values, readyMap, panchayats, paintKey]);

  useEffect(() => {
    const map = readyMap;
    if (!map) return;
    const prev = shownSelected.current;
    if (prev && prev !== selectedPid)
      map.setFeatureState({ source: GP, id: prev }, { selected: false });
    if (selectedPid) map.setFeatureState({ source: GP, id: selectedPid }, { selected: true });
    shownSelected.current = selectedPid;
  }, [selectedPid, readyMap]);

  if (failed) return <>{fallback}</>;

  return (
    <div className="map-frame">
      <div
        ref={containerRef}
        className="map-canvas"
        role="region"
        aria-label={label}
        data-painted={painted === paintKey ? "true" : "false"}
      />
      {hover ? (
        <div className="map-tooltip" aria-hidden="true" style={{ transform: hover.transform }}>
          {renderTooltip(hover.pid)}
        </div>
      ) : null}
    </div>
  );
}
