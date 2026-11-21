import { useCallback, useEffect, useRef, useState } from "react";
import { errMsg } from "./services/api";

export const STATUS_LABEL = {
  NEW: "New", CLASSIFIED: "Classified", ASSIGNED: "Assigned", ACKNOWLEDGED: "Acknowledged", IN_PROGRESS: "In progress",
  RESOLVED: "Resolved", VERIFIED: "Verified", CLOSED: "Closed",
};
export const STATUS_COLOR = {
  NEW: "gray", CLASSIFIED: "blue", ASSIGNED: "indigo", ACKNOWLEDGED: "purple", IN_PROGRESS: "amber", RESOLVED: "green", VERIFIED: "green", CLOSED: "gray",
};
export const ACTION_LABEL = {
  ACKNOWLEDGED: "Acknowledge", IN_PROGRESS: "Start investigation", RESOLVED: "Resolve", VERIFIED: "Verify resolution",
  CLOSED: "Close incident", ASSIGNED: "Return to assigned", CLASSIFIED: "Reclassify",
};

export function fmtDate(v) {
  if (!v) return "-";
  const d = new Date(v);
  return isNaN(d) ? "-" : d.toLocaleString(undefined, { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
export function fmtShort(v) {
  if (!v) return "-";
  const d = new Date(v);
  return isNaN(d) ? "-" : d.toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
export function fmtDuration(seconds) {
  if (seconds == null) return "-";
  const neg = seconds < 0;
  let s = Math.abs(Math.round(seconds));
  const d = Math.floor(s / 86400); s -= d * 86400;
  const h = Math.floor(s / 3600); s -= h * 3600;
  const m = Math.floor(s / 60); s -= m * 60;
  const parts = d ? [`${d}d`, `${h}h`] : h ? [`${h}h`, `${m}m`] : [`${m}m`, `${String(s).padStart(2, "0")}s`];
  return (neg ? "-" : "") + parts.join(" ");
}
export function fmtMinutes(min) {
  if (min == null) return "-";
  if (min < 60) return `${Math.round(min)} min`;
  if (min < 1440) return `${(min / 60).toFixed(1)} h`;
  return `${(min / 1440).toFixed(1)} d`;
}
export const humanize = (s) => (s || "").toString().toLowerCase().replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

/** Load data with loading and error state. Returns {data, loading, error, reload, setData}. */
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const run = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: null }));
    return fnRef.current()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((e) => setState({ data: null, loading: false, error: errMsg(e) }));
  }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { run(); }, deps);
  return { ...state, reload: run, setData: (data) => setState((s) => ({ ...s, data })) };
}

export function useDebounced(value, ms = 400) {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return v;
}

export function usePolling(fn, ms) {
  useEffect(() => {
    const id = setInterval(() => fn(), ms);
    return () => clearInterval(id);
  }, [fn, ms]);
}
