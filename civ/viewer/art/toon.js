// Toon materials: soft three-step light, and the shared "living" touches every material may take:
// wind (sway by height), season (tints and snow on what faces the sky). One place for the look.
import * as THREE from "three";

let ramp = null;
export function toonRamp() {
  if (ramp) return ramp;
  // three soft steps: shade, mid, lit
  const data = new Uint8Array([110, 110, 110, 255, 185, 185, 185, 255, 255, 255, 255, 255]);
  ramp = new THREE.DataTexture(data, 3, 1, THREE.RGBAFormat);
  ramp.minFilter = ramp.magFilter = THREE.NearestFilter;
  ramp.needsUpdate = true;
  return ramp;
}

// uniforms shared by everything alive: time, wind, season and snow (set each frame by the scene)
export const living = {
  uTime: {value: 0},
  uWind: {value: 1},
  uSnow: {value: 0},                       // 0..1 snow lying on what faces up
  uSeason: {value: new THREE.Vector4(0, 0, 0, 0)},   // weights of spring, summer, autumn, winter (sum 1)
};

/**
 * A toon material with options:
 *  color, vertexColors, wind (sway amount, by local height), snow (true: whiteness on upward faces),
 *  foliage (true: per-instance tint `aTint` turns with the seasons), emissive.
 */
export function toon(opts = {}) {
  const m = new THREE.MeshToonMaterial({
    color: opts.color ?? 0xffffff, vertexColors: !!opts.vertexColors, gradientMap: toonRamp(),
    emissive: opts.emissive ?? 0x000000, transparent: !!opts.transparent, opacity: opts.opacity ?? 1,
    side: opts.side ?? THREE.FrontSide,
  });
  const wind = opts.wind || 0, snow = !!opts.snow, foliage = !!opts.foliage;
  if (!wind && !snow && !foliage) return m;
  m.customProgramCacheKey = () => `toon-${wind}-${snow}-${foliage}`;
  m.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, living, {uWindAmt: {value: wind}});
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", `#include <common>
        uniform float uTime; uniform float uWind; uniform float uWindAmt; uniform vec4 uSeason;
        varying vec3 vWPos; varying vec3 vWNormal; varying float vTint;
        ${foliage ? "attribute float aTint;" : ""}`)
      .replace("#include <begin_vertex>", `#include <begin_vertex>
        vec3 basePos = vec3(0.0);
        #ifdef USE_INSTANCING
          basePos = instanceMatrix[3].xyz;
        #endif
        float sway = uWindAmt * uWind * max(0.0, position.y);
        transformed.x += sway * sin(uTime * 1.3 + basePos.x * 0.6 + basePos.z * 0.4);
        transformed.z += sway * 0.6 * sin(uTime * 1.7 + basePos.z * 0.7);
        vTint = ${foliage ? "aTint" : "0.0"};`)
      .replace("#include <worldpos_vertex>", `#include <worldpos_vertex>
        vec4 wp4 = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
          wp4 = instanceMatrix * wp4;
        #endif
        wp4 = modelMatrix * wp4;
        vWPos = wp4.xyz;
        vec3 wn = objectNormal;
        #ifdef USE_INSTANCING
          wn = mat3(instanceMatrix) * wn;
        #endif
        vWNormal = normalize(mat3(modelMatrix) * wn);`);
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", `#include <common>
        uniform float uTime; uniform float uSnow; uniform vec4 uSeason;
        varying vec3 vWPos; varying vec3 vWNormal; varying float vTint;
        float hash12(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
        float vnoise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(hash12(i), hash12(i + vec2(1, 0)), f.x), mix(hash12(i + vec2(0, 1)), hash12(i + vec2(1, 1)), f.x), f.y); }`)
      .replace("#include <color_fragment>", `#include <color_fragment>
        ${foliage ? `
        // leaves through the year: fresh in spring (some in blossom), deep in summer, ochre and red in autumn, bare grey-brown in winter
        vec3 leaf = diffuseColor.rgb;
        vec3 spring = mix(leaf * vec3(1.15, 1.25, 0.95), vec3(1.0, 0.72, 0.82), step(0.82, vTint) * 0.85);
        vec3 autumn = mix(vec3(0.85, 0.55, 0.18), vec3(0.72, 0.25, 0.15), vTint);
        vec3 winter = mix(vec3(0.42, 0.36, 0.30), leaf * 0.75, step(0.6, vTint));
        diffuseColor.rgb = spring * uSeason.x + leaf * uSeason.y + autumn * uSeason.z + winter * uSeason.w;` : ""}
        ${snow ? `
        float up = smoothstep(0.55, 0.85, vWNormal.y);
        float n = vnoise(vWPos.xz * 1.7) * 0.5 + vnoise(vWPos.xz * 6.0) * 0.5;
        float cover = up * smoothstep(1.0 - uSnow, 1.2 - uSnow, n * 0.5 + up * 0.5);
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.95, 0.97, 1.0), cover);` : ""}`);
  };
  return m;
}
