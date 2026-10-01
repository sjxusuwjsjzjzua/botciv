// How people move: a pose for what they are doing (joint angles, in radians), made fresh each frame from
// the time, and the tool they hold for it, chosen from what they really carry. Unknown verbs: idle.

const TOOLKIND = [[/sword/, "sword"], [/spear/, "spear"], [/_axe$|^axe$/, "axe"], [/sickle/, "sickle"], [/knife/, "knife"],
  [/^hammer$/, "hammer"], [/fishing_line|^net$/, "rod"], [/^club$/, "club"], [/^bow$/, "bow"]];
export function held(inv) {
  const have = new Set();
  for (const k of Object.keys(inv || {})) for (const [re, kind] of TOOLKIND) if (re.test(k)) have.add(kind);
  return have;
}

// the tool in the right hand for a verb, if they carry one that fits (a basket for picking is implied)
export function toolFor(verb, detail, have) {
  const d = String(detail || "");
  if (verb === "gather") {
    if (/grain|flax|hay/.test(d)) return have.has("sickle") ? "sickle" : have.has("knife") ? "knife" : null;
    if (d === "wood") return have.has("axe") ? "axe" : null;
    if (/berries|nuts|herbs|fibre|honey|reeds/.test(d)) return "basket";
    return null;
  }
  if (verb === "hunt") return ["spear", "bow", "club", "axe"].find(t => have.has(t)) || null;
  if (verb === "fish") return "rod";
  if (verb === "attack") return ["sword", "spear", "club", "axe", "knife"].find(t => have.has(t)) || null;
  if (verb === "build") return have.has("hammer") ? "hammer" : have.has("axe") ? "axe" : null;
  if (verb === "craft") return have.has("hammer") ? "hammer" : have.has("knife") ? "knife" : null;
  if (verb === "slaughter") return have.has("knife") ? "knife" : null;
  return null;
}

const S = Math.sin;
// a pose: lift (body up/down), lean (forward), roll, head pitch and yaw, each arm's swing (pitch, + forward)
// and spread (roll), each leg's swing, sit (legs forward), lie (asleep)
export function pose(verb, moving, t, seed, talking) {
  const p = {lift: 0, lean: 0, roll: 0, headPitch: 0, headYaw: 0, armL: 0, armR: 0, spreadL: 0.12, spreadR: 0.12, legL: 0, legR: 0,
    sit: 0, lie: false, squash: 1};
  const ph = t * 9 + seed;
  if (moving) {
    const s = S(ph);
    p.legL = s * 0.65; p.legR = -s * 0.65;
    p.armL = -s * 0.55; p.armR = s * 0.55;
    p.lift = Math.abs(S(ph)) * 0.03; p.lean = 0.08;
    p.squash = 1 + Math.abs(S(ph)) * 0.03;
    if (verb === "hunt") { p.armR = -2.4; p.spreadR = 0.05; }
    return p;
  }
  // breathing and looking about, for everyone at rest
  p.squash = 1 + S(t * 2 + seed) * 0.012;
  p.headYaw = S(t * 0.35 + seed) * 0.35;
  switch (verb) {
    case "gather": case "plant": case "take": case "put":
      p.lean = 0.55; p.lift = -0.035; p.headPitch = 0.35;
      p.armR = -0.9 - 0.45 * (0.5 + 0.5 * S(t * 4 + seed)); p.armL = -0.6; p.legL = 0.25; p.legR = -0.1; p.headYaw = 0;
      break;
    case "craft": case "build": case "slaughter": case "fuel": {
      const beat = Math.max(0, S(t * 7 + seed));
      p.lean = 0.2; p.headPitch = 0.35; p.headYaw = 0;
      p.armR = -2.3 + beat * 1.5; p.armL = -0.8;
      p.squash = 1 - beat * 0.03;
      break;
    }
    case "fish":
      p.armR = -1.0 + S(t * 0.8 + seed) * 0.06; p.armL = -0.9; p.spreadL = 0.02; p.headPitch = 0.1; p.headYaw = 0;
      break;
    case "hunt":
      p.armR = -1.7; p.lean = 0.15; p.legL = 0.3; p.legR = -0.3;
      break;
    case "attack": {
      const sw = S(t * 10 + seed);
      p.armR = -1.8 + sw * 1.3; p.lean = 0.25 + sw * 0.1; p.legL = 0.35; p.legR = -0.35; p.headYaw = 0;
      break;
    }
    case "eat":
      p.armR = -1.6 - Math.max(0, S(t * 3 + seed)) * 0.9; p.spreadR = 0.35; p.headPitch = 0.1;
      break;
    case "rest": case "wait":
      p.sit = 1; p.lift = -0.13; p.legL = p.legR = -1.45; p.armL = p.armR = -0.4; p.headPitch = 0.1;
      break;
    case "sleep":
      p.lie = true;
      break;
    case "teach": case "give": case "trade": case "propose": case "tame":
      p.armR = -0.9 + S(t * 3 + seed) * 0.35; p.armL = -0.5; p.headYaw = 0;
      break;
    default:
      p.armL = S(t * 1.1 + seed) * 0.06; p.armR = -S(t * 1.1 + seed) * 0.06;
  }
  if (talking) { p.headPitch += S(t * 6 + seed) * 0.08; p.armL = Math.min(p.armL, -0.5 + S(t * 3.3 + seed) * 0.4); p.spreadL = 0.3; p.headYaw = 0; }
  return p;
}
