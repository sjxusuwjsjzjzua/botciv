// Ready-made models (handoff §5.5 b): CC0 glTF from the Kenney Nature Kit (vendor/models/kenney-nature, its licence
// beside it), loaded and restyled with the kit's toon materials: each model's parts merged into one geometry with its
// materials' colours as vertex colours, scaled to metres, so it instances like a code-made model. ?models=cc0
import * as THREE from "three";
import {GLTFLoader} from "three/addons/GLTFLoader.min.js";
import {mergeGeometries} from "three/addons/BufferGeometryUtils.min.js";

const DIR = "vendor/models/kenney-nature/";

// one geometry from a glTF scene: world transforms applied, colours baked, standing on y = 0, `height` metres tall
export async function loadModel(name, height) {
  const gltf = await new GLTFLoader().loadAsync(DIR + name + ".glb");
  const parts = [];
  gltf.scene.updateMatrixWorld(true);
  gltf.scene.traverse(o => {
    if (!o.isMesh) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    let g = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone();
    g.applyMatrix4(o.matrixWorld);
    const n = g.attributes.position.count, col = new Float32Array(n * 3), c = new THREE.Color();
    const groups = g.groups.length ? g.groups : [{start: 0, count: n, materialIndex: 0}];
    for (const gr of groups) {
      c.copy(mats[gr.materialIndex ?? 0]?.color ?? new THREE.Color(0xffffff));
      for (let i = gr.start; i < gr.start + gr.count && i < n; i++) col.set([c.r, c.g, c.b], i * 3);
    }
    for (const k of Object.keys(g.attributes)) if (k !== "position" && k !== "normal") g.deleteAttribute(k);
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    g.clearGroups();
    parts.push(g);
  });
  const g = mergeGeometries(parts);
  g.computeBoundingBox();
  const bb = g.boundingBox, s = height / (bb.max.y - bb.min.y);
  g.translate(-(bb.min.x + bb.max.x) / 2, -bb.min.y, -(bb.min.z + bb.max.z) / 2);
  g.scale(s, s, s);
  g.computeVertexNormals();
  return g;
}

export async function loadKit() {
  const [oak, pine, bush, rock, stump, logs, camp] = await Promise.all([
    loadModel("tree_oak", 9), loadModel("tree_pineRoundB", 11), loadModel("plant_bushLarge", 1.4), loadModel("rock_largeA", 1.3),
    loadModel("stump_old", 0.7), loadModel("log_stack", 1.0), loadModel("campfire_stones", 0.6)]);
  return {broadleaf: oak, conifer: pine, bush, rock, stump, logs, camp};
}
