// The palette: the land's colours and the light of each hour (docs/viewer.md, section 4).
import * as THREE from "three";

// the land, warm and soft; unknown terrains fall back to grass
export const TERRAIN = {
  ".": {color: 0x8fbf5a, green: 1, height: 0.12},      // grass
  ",": {color: 0x7aa84a, green: 1, height: 0.10},      // rich soil
  "T": {color: 0x5f9443, green: 1, height: 0.16},      // forest floor
  "h": {color: 0xa3a86a, green: 0.6, height: 0.75},    // hills
  "^": {color: 0x9a948a, green: 0.1, height: 1.9},     // mountain
  "~": {color: 0x6c8f7a, green: 0, height: -0.6},      // water bed
  "m": {color: 0x7f9a5e, green: 0.7, height: -0.03},   // marsh
  "s": {color: 0xe3cf98, green: 0, height: 0.04},      // sand
};
export const terrainOf = ch => TERRAIN[ch] || TERRAIN["."];
export const WATER_LEVEL = -0.07;

// the light through the day: keyed by hour of the day (12 a day: dawn 0, night from 9)
const KEYS = [
  // h, sky top, horizon, sun colour, sun strength, ambient (sky), ambient (ground), ambient strength, fog
  [0.0, 0x8fa8d8, 0xf3b8a0, 0xffb38a, 1.1, 0xb8c6e8, 0x6b5a48, 0.85, 0xe9c2ae],
  [1.5, 0x7fb4e6, 0xf7dcb0, 0xffe0b0, 2.0, 0xc7dcf2, 0x6f6450, 1.0, 0xe8dcc4],
  [4.5, 0x6fb0ec, 0xd8ecf7, 0xfff6e8, 2.6, 0xd6e8f8, 0x707058, 1.1, 0xd6e6ee],
  [7.0, 0x7cb0e0, 0xf4dcb4, 0xffd9a0, 2.2, 0xd2dcec, 0x6f6450, 1.0, 0xeedcc0],
  [8.4, 0x6f86c4, 0xf6a77a, 0xff9c62, 1.4, 0xb6b4d8, 0x5a4a40, 0.85, 0xf0b894],
  [9.2, 0x37406f, 0x8f6f9a, 0xa77fb0, 0.45, 0x6c6c9c, 0x302838, 0.6, 0x6e6488],
  [10.5, 0x141c38, 0x2a3458, 0x8fa6e0, 0.32, 0x4a5888, 0x1c1c2c, 0.5, 0x2a3252],
  [11.6, 0x2a3360, 0x6a6a92, 0xc0a0c0, 0.4, 0x6a7098, 0x2a2838, 0.55, 0x5a5878],
  [12.0, 0x8fa8d8, 0xf3b8a0, 0xffb38a, 1.1, 0xb8c6e8, 0x6b5a48, 0.85, 0xe9c2ae],
];
const ca = new THREE.Color(), cb = new THREE.Color();
const mixHex = (a, b, f, out) => out.copy(ca.setHex(a)).lerp(cb.setHex(b), f);

export function lightAt(hour, out = {}) {
  let i = 0;
  while (i < KEYS.length - 2 && KEYS[i + 1][0] <= hour) i++;
  const a = KEYS[i], b = KEYS[i + 1], f = Math.min(1, Math.max(0, (hour - a[0]) / (b[0] - a[0])));
  const ease = f * f * (3 - 2 * f);
  out.top = mixHex(a[1], b[1], ease, out.top || new THREE.Color());
  out.horizon = mixHex(a[2], b[2], ease, out.horizon || new THREE.Color());
  out.sun = mixHex(a[3], b[3], ease, out.sun || new THREE.Color());
  out.sunStrength = a[4] + (b[4] - a[4]) * ease;
  out.skyAmb = mixHex(a[5], b[5], ease, out.skyAmb || new THREE.Color());
  out.groundAmb = mixHex(a[6], b[6], ease, out.groundAmb || new THREE.Color());
  out.ambStrength = a[7] + (b[7] - a[7]) * ease;
  out.fog = mixHex(a[8], b[8], ease, out.fog || new THREE.Color());
  out.night = hour >= 9.2 && hour < 11.8 ? 1 : hour >= 8.6 && hour < 9.2 ? (hour - 8.6) / 0.6 : hour >= 11.8 ? 1 - (hour - 11.8) / 0.2 : 0;
  return out;
}

// the season's weights (spring, summer, autumn, winter), blending into the next over its last days,
// and how much snow lies (it comes in early winter and melts in early spring)
export function seasonAt(seasonIndex, seasonFrac) {
  const w = [0, 0, 0, 0], blend = 0.25, f = seasonFrac > 1 - blend ? (seasonFrac - (1 - blend)) / blend : 0;
  w[seasonIndex] = 1 - f;
  w[(seasonIndex + 1) % 4] += f;
  let snow = 0;
  if (seasonIndex === 3) snow = Math.min(1, seasonFrac / 0.2);
  else if (seasonIndex === 0) snow = Math.max(0, 1 - seasonFrac / 0.25);
  else if (seasonIndex === 2 && seasonFrac > 0.9) snow = (seasonFrac - 0.9) / 0.1 * 0.3;
  return {weights: w, snow};
}
