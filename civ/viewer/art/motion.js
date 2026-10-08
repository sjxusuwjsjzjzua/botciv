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
  if (verb === "craft") {
    const st = craftStyle(detail);
    if (st === "weave" || st === "shape" || st === "grind") return null;          // hands at the work itself
    if (st === "saw" || st === "knap") return have.has("knife") ? "knife" : have.has("axe") ? "axe" : null;
    if (st === "stir") return "ladle";
    return have.has("hammer") ? "hammer" : have.has("knife") ? "knife" : null;
  }
  if (verb === "slaughter") return have.has("knife") ? "knife" : null;
  return null;
}

// the work cycle of a craft, by what is being made (anything else: the hammer's beat)
const CRAFTS = [[/flint|knife|arrow|scraper|stone_axe|blade|sickle|spearhead/, "knap"],
  [/rope|cord|linen|cloth|net|thread|yarn|tunic|cloak|hat|mat|basket|sling|felt/, "weave"],
  [/pot|jar|tablet|brick|bowl|clay|tile|figurine|lamp/, "shape"],
  [/bread|smoked|dried|cheese|stew|flour|beer|ale|butter|salted|porridge|cooked|roast/, "stir"],
  [/plank|wheel|cart|canoe|boat|bow|plough|chair|table|bed|shaft|frame|beam/, "saw"],
  [/poultice|medicine|salve|dye|ink/, "grind"]];
export function craftStyle(detail) {
  const d = String(detail || "");
  for (const [re, k] of CRAFTS) if (re.test(d)) return k;
  return "beat";
}

const S = Math.sin;
// a pose: lift (body up/down), lean (forward), roll, head pitch and yaw, each arm's swing (pitch, + forward)
// and spread (roll), each leg's swing, sit (legs forward), lie (asleep)
export function pose(verb, moving, t, seed, talking, detail, laden = 0) {
  const p = {lift: 0, lean: 0, roll: 0, headPitch: 0, headYaw: 0, armL: 0, armR: 0, spreadL: 0.12, spreadR: 0.12, legL: 0, legR: 0,
    sit: 0, lie: false, squash: 1};
  const ph = t * 9 + seed;
  if (moving) {
    const s = S(ph);
    p.legL = s * 0.65; p.legR = -s * 0.65;
    p.armL = -s * 0.55; p.armR = s * 0.55;
    p.lift = Math.abs(S(ph)) * 0.03; p.lean = 0.08;
    p.squash = 1 + Math.abs(S(ph)) * 0.03;
    if (laden) { p.lean += 0.12 * laden; p.armL *= 0.6; p.armR *= 0.6; }   // a heavy pack: bent under it
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
    case "craft": {
      // each craft its own cycle: knapping strikes low and quick, weaving passes hand over hand, shaping
      // clay turns both hands together, stirring circles, sawing pushes and draws, grinding rocks
      const style = craftStyle(detail);
      p.headPitch = 0.4; p.headYaw = 0; p.lean = 0.25;
      if (style === "knap") {
        const hit = Math.max(0, S(t * 11 + seed));
        p.sit = 1; p.lift = -0.13; p.legL = p.legR = -1.45; p.lean = 0.35;
        p.armL = -0.9; p.armR = -1.5 + hit * 0.7; p.spreadR = 0.05; p.spreadL = 0.25;
      } else if (style === "weave") {
        const a = S(t * 3 + seed);
        p.armL = -1.0 + a * 0.3; p.armR = -1.0 - a * 0.3; p.spreadL = 0.2 + a * 0.1; p.spreadR = 0.2 - a * 0.1;
      } else if (style === "shape") {
        const a = S(t * 2.2 + seed), b = Math.cos(t * 2.2 + seed);
        p.sit = 1; p.lift = -0.13; p.legL = p.legR = -1.45; p.lean = 0.4;
        p.armL = p.armR = -1.1 + a * 0.12; p.spreadL = 0.05 + b * 0.06; p.spreadR = 0.05 - b * 0.06;
      } else if (style === "stir") {
        const a = S(t * 3.5 + seed), b = Math.cos(t * 3.5 + seed);
        p.armR = -1.2 + a * 0.25; p.spreadR = 0.15 + b * 0.15; p.armL = -0.4; p.lean = 0.3;
      } else if (style === "saw") {
        const a = S(t * 5 + seed);
        p.armR = -1.3 + a * 0.45; p.armL = -1.0; p.lean = 0.35 + a * 0.05; p.legL = 0.3; p.legR = -0.2;
      } else if (style === "grind") {
        const a = S(t * 4 + seed);
        p.sit = 1; p.lift = -0.13; p.legL = p.legR = -1.45; p.lean = 0.45;
        p.armL = p.armR = -1.25 + a * 0.18; p.spreadL = p.spreadR = 0.06;
      } else {
        const beat = Math.max(0, S(t * 7 + seed));
        p.lean = 0.2; p.armR = -2.3 + beat * 1.5; p.armL = -0.8; p.squash = 1 - beat * 0.03;
      }
      break;
    }
    case "build": case "slaughter": case "fuel": {
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
