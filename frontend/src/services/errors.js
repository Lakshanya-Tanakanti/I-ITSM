/**
 * Turn any axios error into one readable sentence.
 *
 * Kept free of imports so that it can be unit tested with `node --test` (npm test).
 *
 * Network failure is recognised in three forms:
 *  1. no response at all (server or network down)            -> "Cannot reach the server ..."
 *  2. a timeout (axios code ECONNABORTED or ETIMEDOUT)         -> "The server took too long ..."
 *  3. a gateway/proxy answer without our JSON error body,
 *     e.g. the Vite development proxy returning 500 with an
 *     empty body when the back end is stopped, or 502/503/504
 *     from a reverse proxy                                     -> "Cannot reach the server ..."
 * A JSON body of the form {detail, code} produced by the back end always wins, so a real
 * 503 DATABASE_ERROR from the API is still shown with its own message.
 */
export const NETWORK_MESSAGE = "Cannot reach the server. Is the backend running on port 8000?";
export const TIMEOUT_MESSAGE = "The server took too long to respond.";

const GATEWAY_STATUSES = new Set([502, 503, 504]);

export function isNetworkFailure(e) {
  if (!e) return false;
  if (!e.response) return true;
  const { status, data } = e.response;
  const hasApiBody = data && typeof data === "object" && typeof data.detail === "string";
  if (hasApiBody) return false;
  return GATEWAY_STATUSES.has(status) || status >= 500;
}

export function errMsg(e) {
  if (!e) return "Something went wrong.";
  if (e.code === "ECONNABORTED" || e.code === "ETIMEDOUT") return TIMEOUT_MESSAGE;
  if (isNetworkFailure(e)) return NETWORK_MESSAGE;
  const d = e.response.data;
  if (d && typeof d === "object") {
    const extra = Array.isArray(d.errors)
      ? d.errors.map((x) => (typeof x === "string" ? x : x.message || x.msg || JSON.stringify(x))).filter(Boolean)
      : [];
    const base = typeof d.detail === "string" ? d.detail : "Request failed.";
    return extra.length ? `${base} ${extra.join(" ")}` : base;
  }
  return `Request failed (${e.response.status}).`;
}
