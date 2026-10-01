// Seeds for looks: the same person, place or thing always looks the same.
export function hash(s) {
  let h = 2166136261;
  for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
export const hue = name => hash(name) % 360;

// a small seeded generator (mulberry32): rng() in [0, 1)
export function rng(seed) {
  let a = hash(seed);
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
