// The finishing pass: the scene is drawn into a multisampled target with its depth, then one full-screen pass adds
// the gentle dark outline the target picture has (where depth jumps: silhouettes of roofs, fences, people, trees
// against what lies behind; planes and gentle slopes give none) and a light warm grade.
import * as THREE from "three";

export class Post {
  constructor(renderer, {samples = 4} = {}) {
    this.r = renderer;
    this.rt = new THREE.WebGLRenderTarget(4, 4, {samples, type: THREE.HalfFloatType});
    this.rt.depthTexture = new THREE.DepthTexture(4, 4);
    this.rt.depthTexture.type = THREE.UnsignedIntType;
    this.mat = new THREE.ShaderMaterial({
      uniforms: {tColor: {value: this.rt.texture}, tDepth: {value: this.rt.depthTexture}, uTexel: {value: new THREE.Vector2()},
        uNear: {value: 1}, uFar: {value: 1000}, uStrength: {value: 0.7}, uWidth: {value: 1}, uGrade: {value: 1}},
      vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
      fragmentShader: `
        uniform sampler2D tColor; uniform sampler2D tDepth; uniform vec2 uTexel; uniform float uNear; uniform float uFar;
        uniform float uStrength; uniform float uWidth; uniform float uGrade; varying vec2 vUv;
        float iz(vec2 uv) {            // 1 / view depth: linear across any plane on screen
          float d = texture2D(tDepth, uv).x;
          return (uFar - d * (uFar - uNear)) / (uNear * uFar);
        }
        void main() {
          vec4 c = texture2D(tColor, vUv);
          vec2 o = uTexel * uWidth;
          float z0 = iz(vUv), zl = iz(vUv - vec2(o.x, 0.0)), zr = iz(vUv + vec2(o.x, 0.0)), zd = iz(vUv - vec2(0.0, o.y)), zu = iz(vUv + vec2(0.0, o.y));
          // how far from planar, relative to the depth here; and a step down to something further (the near side)
          float eh = abs(zl + zr - 2.0 * z0) / z0, ev = abs(zd + zu - 2.0 * z0) / z0;
          float e = smoothstep(0.005, 0.022, max(eh, ev));
          float sky = step(0.99999, texture2D(tDepth, vUv).x);
          vec3 col = c.rgb * mix(1.0, 1.0 - uStrength, e * (1.0 - sky * 0.6));
          // warm grade: a touch more saturation and warmth in the mids, as the target
          float l = dot(col, vec3(0.299, 0.587, 0.114));
          col = mix(col, mix(vec3(l), col, 0.94) * vec3(1.02, 1.0, 0.96), uGrade);
          gl_FragColor = vec4(col, 1.0);
          #include <colorspace_fragment>
        }`,
      depthTest: false, depthWrite: false,
    });
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.mat);
    this.quad.frustumCulled = false;
    this.scene = new THREE.Scene(); this.scene.add(this.quad);
    this.ocam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  }

  setSize(w, h, ratio) {
    const W = Math.floor(w * ratio), H = Math.floor(h * ratio);
    this.rt.setSize(W, H);
    this.mat.uniforms.uTexel.value.set(1 / W, 1 / H);
    this.mat.uniforms.uWidth.value = Math.max(1, ratio / 1.6);
  }

  render(scene, cam) {
    const r = this.r;
    r.setRenderTarget(this.rt);
    r.render(scene, cam);
    this.mat.uniforms.uNear.value = cam.near; this.mat.uniforms.uFar.value = cam.far;
    r.setRenderTarget(null);
    r.render(this.scene, this.ocam);
  }
}
