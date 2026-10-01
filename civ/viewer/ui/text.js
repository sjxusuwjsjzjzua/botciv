// Small helpers for words on the page.
export const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
export const pretty = k => String(k ?? "").replace(/_/g, " ");
export const goods = inv => Object.entries(inv || {}).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1])
  .map(([k, n]) => `${n} ${pretty(k)}`).join(", ");
export const skillWord = v => v >= 0.7 ? "master" : v >= 0.3 ? "able" : v > 0 ? "beginner" : "untried";
export const DOING = {gather: "gathering", hunt: "hunting", fish: "fishing", craft: "making", build: "building", plant: "sowing",
  eat: "eating", rest: "resting", sleep: "sleeping", wait: "waiting", go: "walking", take: "fetching", put: "putting away",
  give: "giving", trade: "trading", teach: "teaching", study: "studying", attack: "fighting", follow: "following",
  tame: "taming", slaughter: "butchering", fuel: "tending a fire", "": "idle"};
export function doing(now, nameOf) {
  if (!now) return "";
  const v = DOING[now.verb] ?? pretty(now.verb), d = now.detail;
  if (d === "" || d == null) return v;
  if (typeof d === "number") return `${v} ${nameOf(d)}`;
  return `${v} ${pretty(d)}`;
}
