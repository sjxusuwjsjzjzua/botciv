// The scrubber, with the marks of what happened along it (births, deaths, firsts, blows, monuments).
const MARK = {birth: "#5f8a3c", death: "#7d6b55", first: "#d29a2c", attack: "#a63d32", monument: "#6f9fc4", group: "#8a5aa8", law: "#8a5aa8",
  raid: "#c2412f", plunder: "#c2412f", repelled: "#a67c32", fealty: "#b08d2c", peace: "#4f8fae", broke_peace: "#c2412f"};

export class Timeline {
  constructor(input, canvas, store, onScrub) {
    this.input = input; this.cv = canvas; this.store = store;
    input.min = store.first; input.max = store.last;
    input.addEventListener("input", () => onScrub(+input.value));
    this.drawn = 0;
    addEventListener("resize", () => { this.drawn = 0; });
  }

  show(t) {
    if (document.activeElement !== this.input) this.input.value = t;
    const r = this.cv.getBoundingClientRect(), dpr = devicePixelRatio || 1;
    if (this.drawn === r.width) return;
    this.drawn = r.width;
    this.cv.width = r.width * dpr; this.cv.height = r.height * dpr;
    const g = this.cv.getContext("2d"), s = this.store, span = Math.max(1, s.last - s.first);
    g.scale(dpr, dpr);
    for (const e of s.events) {
      const c = MARK[e.kind];
      if (!c) continue;
      g.fillStyle = c;
      const x = (e.t - s.first) / span * r.width;
      g.fillRect(x, e.kind === "birth" || e.kind === "death" ? 6 : 0, 1.5, e.kind === "first" || e.kind === "monument" ? r.height : 6);
    }
  }
}
