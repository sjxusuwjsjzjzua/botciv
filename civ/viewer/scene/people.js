// People in the land: each a small figure (body, head, hair, eyes, feet), drawn as shared instanced parts,
// coloured by who they are and what they wear, sized by age, walking smoothly between the recorded hours.
// .pos: id -> where they stand now (for the camera, picking and the words over heads).
import * as THREE from "three";
import {toon} from "../art/toon.js";
import {rng} from "../art/look.js";

const SKIN = [0xf6d5b8, 0xeec39a, 0xd9a47a, 0xb97d55, 0x8d5a3b, 0x6b4430];
const HAIR = [0x2b2018, 0x4a3020, 0x7a4a26, 0xb07a3e, 0xd8b06a, 0x8a3a20, 0x1c1c22];
const CLOTH = {material: 0xb08458, hide: 0xa0744c, linen: 0xe9dfc8, wool: 0x8fa0b8, fine: 0xb0473a, fur: 0x7a5a3e};

function looksOf(person, store) {
  // children take after their parents: their colours come from a parent's seed half the time
  const r = rng("look" + person.id), pr = person.parents?.length ? rng("look" + person.parents[Math.floor(r() * person.parents.length)]) : null;
  const pick = (arr, a, b) => arr[Math.floor(((b && a() < 0.6) ? b() : a()) * arr.length)];
  return {skin: pick(SKIN, r, pr), hair: pick(HAIR, r, pr), style: Math.floor(r() * 3), height: 0.92 + r() * 0.16, round: 0.9 + r() * 0.2};
}

function garment(inv, cat) {
  // the warmest or finest thing worn on the body: its colour
  const worn = Object.keys(inv || {}).filter(k => cat.items[k]?.class === "worn");
  const body = worn.find(k => /coat|cloak|robe/.test(k)) || worn.find(k => /tunic/.test(k));
  if (!body) return CLOTH.material;
  if (/fur/.test(body)) return CLOTH.fur;
  if (/wool/.test(body)) return CLOTH.wool;
  if (/linen/.test(body)) return CLOTH.linen;
  if (/fine|robe/.test(body)) return CLOTH.fine;
  return CLOTH.hide;
}

export class People {
  constructor(scene, land, store) {
    this.scene = scene; this.land = land; this.s = store;
    this.pos = new Map();
    this.face = new Map();
    this.looks = new Map();
    this.cap = 0;
    const body = new THREE.CapsuleGeometry(0.11, 0.12, 4, 10); body.translate(0, 0.2, 0);
    const head = new THREE.SphereGeometry(0.13, 16, 12); head.translate(0, 0.43, 0);
    const hair = new THREE.SphereGeometry(0.138, 16, 10, 0, Math.PI * 2, 0, Math.PI * 0.55); hair.translate(0, 0.445, -0.005);
    const eye = new THREE.SphereGeometry(0.018, 8, 6);
    const foot = new THREE.SphereGeometry(0.045, 8, 6); foot.scale(1, 0.6, 1.4);
    this.geos = {body, head, hair, eyeL: eye, eyeR: eye, footL: foot, footR: foot};
    this.mats = {body: toon({color: 0xffffff}), head: toon({color: 0xffffff}), hair: toon({color: 0xffffff}),
      eyeL: new THREE.MeshBasicMaterial({color: 0x2a2018}), eyeR: new THREE.MeshBasicMaterial({color: 0x2a2018}),
      footL: toon({color: 0x5a3d26}), footR: toon({color: 0x5a3d26})};
    this.meshes = {};
    this.o = new THREE.Object3D(); this.m = new THREE.Matrix4(); this.part = new THREE.Matrix4(); this.c = new THREE.Color();
  }

  ensure(n) {
    if (n <= this.cap) return;
    this.cap = Math.ceil(n * 1.3) + 16;
    for (const [k, g] of Object.entries(this.geos)) {
      if (this.meshes[k]) { this.scene.remove(this.meshes[k]); this.meshes[k].dispose(); }
      const m = new THREE.InstancedMesh(g, this.mats[k], this.cap);
      m.castShadow = k === "body" || k === "head";
      m.frustumCulled = false;
      m.count = 0;
      this.scene.add(m);
      this.meshes[k] = m;
    }
  }

  update(view, t, dt) {
    const s = this.s, a = s.hour(t), b = s.nextHour(t);
    if (!a) return;
    const snap = s.snapshot(t), f = t - Math.floor(t);
    this.ensure(a.people.size);
    const M = this.meshes, o = this.o, now = performance.now() / 1000;
    let i = 0;
    this.pos.clear();
    for (const [id, p] of a.people) {
      const q = b?.people.get(id) || p;
      const person = s.person(id);
      if (!person) continue;
      if (!this.looks.has(id)) this.looks.set(id, looksOf(person, s));
      const look = this.looks.get(id);
      // where: between this hour's place and the next, eased; facing the way they go
      const e = f * f * (3 - 2 * f), x = p.x + 0.5 + (q.x - p.x) * e, z = p.y + 0.5 + (q.y - p.y) * e;
      const moving = q.x !== p.x || q.y !== p.y, y = this.land.groundAt(x, z);
      if (moving) this.face.set(id, Math.atan2(q.x - p.x, q.y - p.y));
      const yaw = this.face.get(id) ?? (id % 8) * 0.8;
      this.pos.set(id, new THREE.Vector3(x, y, z));
      const age = s.age(id, t), grown = Math.min(1, 0.45 + age / 16 * 0.55), scale = grown * look.height;
      const verb = p.verb, asleep = verb === "sleep" || (verb === "rest" && s.cal.of(t).night);
      const step = moving ? Math.sin(now * 10 + id) : 0, bob = moving ? Math.abs(step) * 0.03 : Math.sin(now * 2 + id) * 0.006;
      const work = ["gather", "craft", "build", "plant", "fish", "slaughter", "fuel"].includes(verb) && !moving;
      const bend = work ? 0.25 + 0.12 * Math.sin(now * 6 + id) : 0;
      o.position.set(x, y + bob, z);
      o.rotation.set(asleep ? -Math.PI / 2 : bend, yaw, 0, "YXZ");
      if (asleep) o.position.y += 0.08;
      o.scale.set(scale * look.round, scale, scale * look.round);
      o.updateMatrix();
      const set = (k, local, color) => {
        this.m.multiplyMatrices(o.matrix, local);
        M[k].setMatrixAt(i, this.m);
        if (color != null) M[k].setColorAt(i, this.c.setHex(color));
      };
      const I = this.part.identity();
      set("body", I, garment(snap?.people.get(id)?.inv, s.cat));
      set("head", I, look.skin);
      set("hair", I, look.hair);
      set("eyeL", new THREE.Matrix4().makeTranslation(-0.045, 0.44, 0.118));
      set("eyeR", new THREE.Matrix4().makeTranslation(0.045, 0.44, 0.118));
      set("footL", new THREE.Matrix4().makeTranslation(-0.05, 0.02 + Math.max(0, step) * 0.04, step * 0.05));
      set("footR", new THREE.Matrix4().makeTranslation(0.05, 0.02 + Math.max(0, -step) * 0.04, -step * 0.05));
      i++;
    }
    for (const m of Object.values(M)) {
      m.count = i;
      m.instanceMatrix.needsUpdate = true;
      if (m.instanceColor) m.instanceColor.needsUpdate = true;
    }
  }
}
