// Water and ways as ribbons along their curves: the river and the stream (toon water: a deeper middle, a light edge
// line where it meets the bank, slow streaks drifting with the flow, a glint of sun), and the worn track between
// settlements (soft-edged earth). Ribbons follow the land's curve exactly and are pulled a little toward the camera
// in depth only (never on screen), so the coarse land far off never hides a river or a road.
import * as THREE from "three";
import {living} from "../art/toon.js";

// a ribbon along a Curve: `cols` vertices across, one row every `step` metres; y(x, z, across) gives the height
export function ribbon(curve, {step = 6, cols = 5, widthScale = 1, y, from = 0, to = curve.length}) {
  const rows = Math.max(2, Math.ceil((to - from) / step) + 1);
  const pos = new Float32Array(rows * cols * 3), uv = new Float32Array(rows * cols * 2);
  for (let r = 0; r < rows; r++) {
    const s = from + (to - from) * r / (rows - 1), p = curve.at(s);
    // the direction smoothed over a few metres, so the edges never kink at the curve's corners
    const a = curve.at(s - 4), b = curve.at(s + 4);
    let dx = b.x - a.x, dy = b.y - a.y; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
    const hw = p.w / 2 * widthScale;
    for (let c = 0; c < cols; c++) {
      const t = c / (cols - 1) * 2 - 1, X = p.x - dy * hw * t, Y = p.y + dx * hw * t, k = r * cols + c;
      pos[k * 3] = X; pos[k * 3 + 1] = y(X, Y, t, s); pos[k * 3 + 2] = Y;
      uv[k * 2] = s; uv[k * 2 + 1] = t;
    }
  }
  const idx = [];
  for (let r = 0; r < rows - 1; r++) for (let c = 0; c < cols - 1; c++) {
    const p = r * cols + c, q = p + 1, u = p + cols, v = u + 1;
    idx.push(p, q, u, q, v, u);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  g.computeBoundingSphere();
  return g;
}

const BIAS = `
  vec4 wpos = modelMatrix * vec4(position, 1.0);
  vec3 toCam = cameraPosition - wpos.xyz;
  float camD = length(toCam);
  wpos.xyz += toCam / camD * min(camD * 0.003 + 0.04, 60.0);`;

export function waterMaterial(light) {
  const m = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, fog: true,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, {
      uDeep: {value: new THREE.Color(0x5f8fa8)}, uShallow: {value: new THREE.Color(0x8fb6c0)}, uEdge: {value: new THREE.Color(0xe8f0e4)},
      uSky: {value: new THREE.Color(0xcfe0ea)}, uSun: {value: new THREE.Color(0xfff0d0)}, uWidth: {value: 40},
    }]),
    vertexShader: `
      uniform float uTime; varying vec2 vUv; varying vec3 vW;
      #include <fog_pars_vertex>
      void main() {
        vUv = uv;
        ${BIAS}
        vW = wpos.xyz;
        vec4 mvPosition = viewMatrix * wpos;
        gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: `
      uniform vec3 uDeep; uniform vec3 uShallow; uniform vec3 uEdge; uniform vec3 uSky; uniform vec3 uSun; uniform float uTime;
      uniform float uWidth; uniform float uLight; uniform float uNight; varying vec2 vUv; varying vec3 vW;
      #include <fog_pars_fragment>
      float h1(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
      float n2(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(h1(i), h1(i + vec2(1, 0)), f.x), mix(h1(i + vec2(0, 1)), h1(i + vec2(1, 1)), f.x), f.y); }
      void main() {
        float a = abs(vUv.y), s = vUv.x;
        float across = vUv.y * uWidth * 0.5;
        vec3 col = mix(uDeep, uShallow, smoothstep(0.25, 0.92, a));
        // streaks drifting with the flow
        float f = n2(vec2(s * 0.06 - uTime * 0.35, across * 0.22)) * 0.6 + n2(vec2(s * 0.19 - uTime * 0.8, across * 0.6)) * 0.4;
        col = mix(col, uSky, smoothstep(0.62, 0.8, f) * 0.45);
        col += uSun * smoothstep(0.93, 0.99, n2(vec2(s * 0.9 - uTime * 1.3, across * 1.7 + uTime * 0.2))) * 0.35;
        // the light line where water meets the bank, gently moving
        float edge = smoothstep(0.84, 0.9, a + (n2(vec2(s * 0.3 + uTime * 0.4, 1.0)) - 0.5) * 0.05);
        col = mix(col, uEdge, edge * 0.6);
        col *= uLight;
        gl_FragColor = vec4(col, (1.0 - smoothstep(0.93, 1.0, a)) * 0.96);
        #include <fog_fragment>
      }`,
  });
  m.uniforms.uTime = living.uTime;
  m.uniforms.uLight = light;
  m.uniforms.uNight = living.uNight;
  return m;
}

// the worn way: warm earth, darker in the ruts, fading out at its edges
export function wayMaterial(light, color = 0xcfb283) {
  const m = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, fog: true,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, THREE.UniformsLib.lights, {
      uCol: {value: new THREE.Color(color)}, uRut: {value: new THREE.Color(0xb08a58)},
    }]),
    lights: false,
    vertexShader: `
      varying vec2 vUv; varying vec3 vW;
      #include <fog_pars_vertex>
      void main() {
        vUv = uv;
        ${BIAS}
        vW = wpos.xyz;
        vec4 mvPosition = viewMatrix * wpos;
        gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: `
      uniform vec3 uCol; uniform vec3 uRut; uniform vec3 uLightCol; varying vec2 vUv; varying vec3 vW;
      #include <fog_pars_fragment>
      float h1(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
      float n2(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(h1(i), h1(i + vec2(1, 0)), f.x), mix(h1(i + vec2(0, 1)), h1(i + vec2(1, 1)), f.x), f.y); }
      void main() {
        float a = abs(vUv.y);
        float wob = (n2(vec2(vUv.x * 0.15, 3.0)) - 0.5) * 0.35 + (n2(vec2(vUv.x * 0.9, 7.0)) - 0.5) * 0.15;
        float alpha = 1.0 - smoothstep(0.55, 1.0, a + wob);
        vec3 col = mix(uCol, uRut, smoothstep(0.15, 0.0, abs(abs(vUv.y) - 0.42)) * 0.35);
        col *= 0.92 + 0.16 * n2(vW.xz * 0.7);
        col *= uLightCol;
        gl_FragColor = vec4(col, alpha);
        #include <fog_fragment>
      }`,
  });
  m.uniforms.uLightCol = light;
  return m;
}
