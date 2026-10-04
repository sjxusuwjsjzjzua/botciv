// Format 3 decoding: the only place that knows the positions in the recorded lists (docs/viewer.md,
// section 3). Lists only ever grow at the end, so a missing field reads as its default.
export const FORMAT = 3;

// an hour's person: [id, x, y, health, fullness, verb, detail]
export const hourPerson = a => ({id: a[0], x: a[1], y: a[2], health: a[3], fullness: a[4], verb: a[5] || "", detail: a[6] ?? ""});
// an hour's herd: [id, kind, x, y, n]; a pack of wolves: [id, x, y, n]
export const herd = a => ({id: a[0], kind: a[1], x: a[2], y: a[3], n: a[4]});
export const pack = a => ({id: a[0], x: a[1], y: a[2], n: a[3]});

// a snapshot's building: [id, kind, x, y, owner, done, hp, inv, animals, working, crop, access, growth, built (0-1)]
export const building = a => ({
  id: a[0], kind: a[1], x: a[2], y: a[3], owner: a[4], done: !!a[5], hp: a[6], inv: a[7] || {}, animals: a[8] || {},
  working: !!a[9], crop: a[10] || null, access: a[11] ?? null,
  growth: a[12] ? {sown: a[12][0], ripeAt: a[12][1], ripe: !!a[12][2]} : null,
  built: a[13] ?? (a[5] ? 1 : 0.4),
});
// a snapshot's deposit: [key "x,y", kind, left]
export const deposit = a => { const [x, y] = a[0].split(",").map(Number); return {x, y, kind: a[1], left: a[2]}; };
// a snapshot's person: [inv, skills, home, partner, groups, goal]
export const snapPerson = a => ({inv: a[0] || {}, skills: a[1] || {}, home: a[2] ?? null, partner: a[3] ?? null, groups: a[4] || [], goal: a[5] ?? null});
// a snapshot's group: [id, name, leader, members, decide, dues, treasury, laws, founded, dissolved, rules]
export const group = a => ({id: a[0], name: a[1], leader: a[2], members: a[3] || [], decide: a[4], dues: a[5] || {},
  treasury: a[6] ?? null, laws: a[7] || [], founded: a[8], dissolved: a[9] ?? null, rules: a[10] || ""});
// an event: [t, kind, text, who, {craft, group, cause...}]
export const event = a => ({t: a[0], kind: a[1], text: a[2], who: a[3] || [], data: a[4] || {}});
// a chunk's thought: [t, id, thought, goal, say]
export const thought = a => ({t: a[0], id: a[1], thought: a[2], goal: a[3], say: a[4]});
// a mind's own record: [t, thought, goal, plan, say, to, model]
export const decision = a => ({t: a[0], thought: a[1], goal: a[2], plan: a[3] || [], say: a[4], to: a[5], model: a[6]});
