// The land's colour maps, painted off the main thread (demo/live.js): told the land once, then asked for a box at a
// size; answers its pixels (RGBA, row by row from the box's corner). With `water`, sea, lakes and rivers are painted
// as water (seen from far off, where no sheet or ribbon of water is drawn over them).
import {LandTiles} from "./tiles.js";

let land = null;
const WATER = [0.36, 0.55, 0.62];
onmessage = e => {
  const m = e.data;
  if (m.land) { land = new LandTiles(m.land); return; }
  const [bx, by, bw, bh] = m.box, [w, h] = m.size, data = new Uint8Array(w * h * 4), c = [0, 0, 0];
  for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
    land.color(bx + (i + 0.5) / w * bw, by + (j + 0.5) / h * bh, c);
    if (m.water && land.r.water > 0) {
      const k = Math.min(1, land.r.water / 1.2) * 0.9;
      for (let n = 0; n < 3; n++) c[n] = c[n] + (WATER[n] - c[n]) * k;
    }
    const o = (j * w + i) * 4;
    data[o] = Math.min(255, c[0] * 255); data[o + 1] = Math.min(255, c[1] * 255); data[o + 2] = Math.min(255, c[2] * 255); data[o + 3] = 255;
  }
  postMessage({id: m.id, data, w, h, box: m.box}, [data.buffer]);
};
