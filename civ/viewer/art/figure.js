// The people's figures: chibi proportions (a big round head, a small pear body, short limbs), each part
// built around its joint so that animation is only turning joints. Heights are in tiles: a grown person
// stands about 0.72 tall before their own scale. Every part is coloured per person (instance colours).
import * as THREE from "three";
import {mergeGeometries, mergeVertices} from "three/addons/BufferGeometryUtils.min.js";

export const JOINT = {
  hip: 0.17, legX: 0.055,
  shoulder: 0.34, armX: 0.125,
  neck: 0.4,
};

const smooth = g => { g.deleteAttribute("uv"); g.deleteAttribute("normal"); g = mergeVertices(g, 1e-4); g.computeVertexNormals(); return g; };
const merged = gs => smooth(mergeGeometries(gs.map(g => { const y = g.index ? g.toNonIndexed() : g; return y; })));
const sphere = (r, ws = 14, hs = 10) => new THREE.SphereGeometry(r, ws, hs);

export function parts(lod = 0) {
  const seg = lod ? 0.6 : 1, n = k => Math.max(5, Math.round(k * seg));
  // body: a soft pear, from the hips up to the shoulders (pivot at the hips)
  const body = sphere(0.14, n(14), n(10)); body.scale(1, 1.15, 0.85); body.translate(0, 0.08, 0);
  // head (pivot at the neck)
  const head = sphere(0.17, n(18), n(14)); head.translate(0, 0.16, 0);
  // limbs hang down from their joints
  const arm = new THREE.CapsuleGeometry(0.034, 0.08, 3, n(8)); arm.translate(0, -0.07, 0);
  const hand = sphere(0.04, n(8), n(6)); hand.translate(0, -0.15, 0);
  const leg = new THREE.CapsuleGeometry(0.042, 0.06, 3, n(8)); leg.translate(0, -0.06, 0);
  const foot = sphere(0.05, n(8), n(6)); foot.scale(1, 0.6, 1.35); foot.translate(0, -0.135, 0.02);
  // the face (in the head's frame)
  const eye = sphere(0.031, 10, 8); eye.scale(0.85, 1.25, 0.5);
  const shine = sphere(0.011, 6, 4);
  const blush = sphere(0.03, 10, 6); blush.scale(1.2, 0.6, 0.3);
  return {body, head, arm, hand, leg, foot, eye, shine, blush};
}

// hair styles, in the head's frame: a cap with a style's own shape
export function hairs() {
  const cap = () => { const g = sphere(0.182, 18, 12); g.scale(1, 0.95, 1); const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) if (p.getY(i) < -0.02) p.setY(i, -0.02 + (p.getY(i) + 0.02) * 0.15);    // flattened under the brow
    g.translate(0, 0.19, -0.012); return g; };
  const fringe = () => { const g = sphere(0.1, 10, 6); g.scale(1.5, 0.42, 0.6); g.translate(0, 0.295, 0.115); return g; };
  const short = merged([cap(), fringe()]);
  const puff = (x, y, z, r, sx = 1, sy = 1, sz = 1) => { const g = sphere(r, 12, 8); g.scale(sx, sy, sz); g.translate(x, y, z); return g; };
  const bob = merged([cap(), fringe(), puff(-0.15, 0.1, -0.02, 0.085, 0.8, 1.2, 1), puff(0.15, 0.1, -0.02, 0.085, 0.8, 1.2, 1), puff(0, 0.11, -0.12, 0.13, 1.25, 1.0, 0.7)]);
  const long = merged([cap(), fringe(), (() => { const g = sphere(0.16, 14, 10); g.scale(1.1, 1.3, 0.55); g.translate(0, 0.06, -0.1); return g; })()]);
  const bun = merged([cap(), fringe(), (() => { const g = sphere(0.075, 10, 8); g.translate(0, 0.36, -0.08); return g; })()]);
  const tufty = merged([cap(), ...[-0.06, 0, 0.06].map((x, i) => { const g = new THREE.ConeGeometry(0.04, 0.12, 6); g.rotateX(-0.5 + i * 0.1); g.translate(x, 0.37, 0.04); return g; })]);
  return {short, bob, long, bun, tufty};
}
export const HAIR_STYLES = ["short", "bob", "long", "bun", "tufty"];

// far off: one plain cap of hair for every style
export function hairFar() { const g = sphere(0.18, 10, 6); g.scale(1, 0.95, 1); g.translate(0, 0.2, -0.015); return g; }

// worn things
export function wear() {
  const hat = new THREE.ConeGeometry(0.2, 0.16, 16); hat.translate(0, 0.38, 0);
  const brim = new THREE.CylinderGeometry(0.24, 0.24, 0.015, 18); brim.translate(0, 0.3, 0);
  const strawHat = mergeGeometries([hat.toNonIndexed(), brim.toNonIndexed()]); strawHat.computeVertexNormals();
  const furHat = new THREE.CylinderGeometry(0.17, 0.19, 0.14, 16); furHat.translate(0, 0.33, 0);
  // a cape hangs from the shoulders behind (pivot at the shoulders' height)
  const cape = new THREE.CylinderGeometry(0.15, 0.2, 0.3, 14, 1, true, Math.PI * 0.5, Math.PI); cape.translate(0, -0.13, -0.01);
  const robe = new THREE.CylinderGeometry(0.13, 0.19, 0.2, 14, 1, true); robe.translate(0, -0.06, 0);
  const necklace = new THREE.TorusGeometry(0.09, 0.012, 6, 16); necklace.rotateX(Math.PI / 2 - 0.3); necklace.translate(0, 0.0, 0.02);
  // a pack on the back, bound with a strap (pivot at the shoulders' height; scaled by the load)
  const sack = new THREE.SphereGeometry(0.11, 12, 9); sack.scale(1.05, 1.15, 0.75); sack.translate(0, -0.07, -0.16);
  const strap = new THREE.TorusGeometry(0.115, 0.012, 5, 14); strap.rotateY(Math.PI / 2); strap.translate(0, -0.05, -0.07);
  const pack = mergeGeometries([sack.toNonIndexed(), strap.toNonIndexed()]); pack.computeVertexNormals();
  return {strawHat, furHat, cape, robe, necklace, pack};
}

// things held (in the hand's frame: the hand at the origin, the arm above it, the palm facing forward)
export function tools() {
  const stick = (len, r = 0.012) => { const g = new THREE.CylinderGeometry(r, r, len, 6); g.rotateX(Math.PI / 2); g.translate(0, -0.15, len / 2 - 0.08); return g; };
  const at = (g, z) => { g.translate(0, -0.15, z); return g; };
  const mk = gs => { const g = mergeGeometries(gs.map(x => (x.index ? x.toNonIndexed() : x))); g.computeVertexNormals(); return g; };
  const spearHead = new THREE.ConeGeometry(0.025, 0.08, 6); spearHead.rotateX(Math.PI / 2);
  const axeHead = new THREE.BoxGeometry(0.02, 0.07, 0.05);
  const hammerHead = new THREE.BoxGeometry(0.05, 0.04, 0.04);
  const blade = new THREE.TorusGeometry(0.05, 0.008, 4, 10, Math.PI); blade.rotateY(Math.PI / 2);
  const swordBlade = new THREE.BoxGeometry(0.02, 0.008, 0.28);
  const club = new THREE.CylinderGeometry(0.03, 0.014, 0.24, 7); club.rotateX(Math.PI / 2);
  const basket = new THREE.CylinderGeometry(0.06, 0.045, 0.06, 10); basket.translate(0, -0.2, 0.03);
  const bowArc = new THREE.TorusGeometry(0.16, 0.008, 4, 14, Math.PI); bowArc.rotateZ(Math.PI / 2);
  return {
    spear: mk([stick(0.5), at(spearHead.clone(), 0.44)]),
    axe: mk([stick(0.22), at(axeHead.clone(), 0.13)]),
    hammer: mk([stick(0.18), at(hammerHead.clone(), 0.1)]),
    sickle: mk([stick(0.1), at(blade.clone(), 0.08)]),
    knife: mk([at(new THREE.BoxGeometry(0.01, 0.015, 0.1), 0.04)]),
    rod: mk([stick(0.55, 0.008)]),
    club: mk([at(club.clone(), 0.1)]),
    sword: mk([stick(0.06), at(swordBlade.clone(), 0.18)]),
    basket: mk([basket]),
    bow: mk([at(bowArc.clone(), 0.02)]),
    ladle: mk([stick(0.2, 0.01), at(new THREE.SphereGeometry(0.03, 8, 6), 0.14)]),
  };
}
export const TOOL_COLOR = {spear: 0x8a6a44, axe: 0x8a8f96, hammer: 0x7a6a5a, sickle: 0xa0a4aa, knife: 0xb0b4ba, rod: 0x9a7a4e,
  club: 0x7a5534, sword: 0xc0c6cc, basket: 0xc9a66b, bow: 0x8a5a2b, ladle: 0x9a7a4e};
