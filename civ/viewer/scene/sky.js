// The sky and the light: a dome coloured by the hour, the sun (or the moon) casting soft shadows, the
// ambient light of sky and ground, the haze, stars at night, and what falls in its season (snow, leaves).
import * as THREE from "three";
import {lightAt, seasonAt} from "../art/palette.js";
import {living} from "../art/toon.js";

export class Sky {
  constructor(scene, quality = "high") {
    this.scene = scene;
    this.L = {};
    // the dome
    this.domeMat = new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: {uTop: {value: new THREE.Color()}, uHorizon: {value: new THREE.Color()}, uNight: {value: 0}, uTime: living.uTime},
      vertexShader: `varying vec3 vDir; void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: `uniform vec3 uTop; uniform vec3 uHorizon; uniform float uNight; varying vec3 vDir;
        float h(vec3 p) { return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
        void main() {
          float y = clamp(vDir.y, 0.0, 1.0);
          vec3 c = mix(uHorizon, uTop, pow(y, 0.6));
          vec3 q = floor(vDir * 180.0);
          float star = step(0.9965, h(q)) * smoothstep(0.05, 0.3, vDir.y) * uNight;
          gl_FragColor = vec4(c + star * 0.9, 1.0);
        }`,
    });
    this.dome = new THREE.Mesh(new THREE.SphereGeometry(400, 32, 16), this.domeMat);
    this.dome.renderOrder = -1;
    scene.add(this.dome);
    // lights
    this.hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1);
    scene.add(this.hemi);
    this.sun = new THREE.DirectionalLight(0xffffff, 2);
    this.sun.castShadow = true;
    const size = quality === "high" ? 2048 : 1024;
    this.sun.shadow.mapSize.set(size, size);
    this.sun.shadow.bias = -0.0008;
    this.sun.shadow.normalBias = 0.03;
    this.sun.shadow.radius = 3;
    scene.add(this.sun, this.sun.target);
    scene.fog = new THREE.Fog(0xffffff, 60, 260);
    // what falls
    this.fall = this.makeFall(quality === "high" ? 2500 : 1200);
    scene.add(this.fall);
  }

  makeFall(n) {
    const pos = new Float32Array(n * 3), seed = new Float32Array(n);
    for (let i = 0; i < n; i++) { pos[i * 3] = Math.random() * 60 - 30; pos[i * 3 + 1] = Math.random() * 20; pos[i * 3 + 2] = Math.random() * 60 - 30; seed[i] = Math.random(); }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));
    const m = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false,
      uniforms: {uTime: living.uTime, uKind: {value: 0}, uAmount: {value: 0}, uCenter: {value: new THREE.Vector3()}, uScale: {value: 1}},
      vertexShader: `uniform float uTime; uniform float uKind; uniform vec3 uCenter; uniform float uScale; attribute float aSeed; varying float vSeed;
        void main() {
          vSeed = aSeed;
          float speed = uKind < 0.5 ? 1.2 : 0.7;
          vec3 p = position;
          p.y = mod(p.y - uTime * speed * (0.6 + aSeed * 0.8), 20.0);
          p.x += sin(uTime * 0.8 + aSeed * 30.0) * (uKind < 0.5 ? 0.5 : 1.2);
          p.z += cos(uTime * 0.6 + aSeed * 20.0) * 0.4;
          vec4 mv = modelViewMatrix * vec4(p * vec3(uScale, 1.0, uScale) + uCenter, 1.0);
          gl_Position = projectionMatrix * mv;
          gl_PointSize = (uKind < 0.5 ? 70.0 : 90.0) / -mv.z;
        }`,
      fragmentShader: `uniform float uKind; uniform float uAmount; varying float vSeed;
        void main() {
          vec2 c = gl_PointCoord - 0.5;
          float d = length(c);
          if (uKind < 0.5) { if (d > 0.5) discard; gl_FragColor = vec4(1.0, 1.0, 1.0, (1.0 - d * 2.0) * uAmount * 0.9); }
          else { if (abs(c.x) + abs(c.y) * 1.8 > 0.5) discard; vec3 leaf = mix(vec3(0.9, 0.5, 0.15), vec3(0.75, 0.25, 0.15), vSeed);
                 gl_FragColor = vec4(leaf, uAmount * step(vSeed, 0.35)); }
        }`,
    });
    const pts = new THREE.Points(g, m);
    pts.frustumCulled = false;
    return pts;
  }

  // the light and weather at a moment
  update(cal, target, dist) {
    const L = lightAt(cal.hour + (cal.t % 1), this.L);
    this.domeMat.uniforms.uTop.value.copy(L.top);
    this.domeMat.uniforms.uHorizon.value.copy(L.horizon);
    this.domeMat.uniforms.uNight.value = L.night;
    this.hemi.color.copy(L.skyAmb); this.hemi.groundColor.copy(L.groundAmb); this.hemi.intensity = L.ambStrength;
    // the sun crosses the sky by day (hours 0..9); the moon by night
    const h = cal.hour + (cal.t % 1), day = h < 9.2;
    const a = day ? Math.PI * (0.06 + 0.88 * h / 9.2) : Math.PI * (0.25 + 0.5 * (h - 9.2) / 2.8);
    const dir = new THREE.Vector3(Math.cos(a) * 0.9, Math.max(0.25, Math.sin(a)), 0.45).normalize();
    this.sun.color.copy(L.sun); this.sun.intensity = L.sunStrength;
    const span = Math.min(90, Math.max(18, dist * 0.9));
    this.sun.position.copy(target).addScaledVector(dir, 80);
    this.sun.target.position.copy(target);
    const sc = this.sun.shadow.camera;
    sc.left = sc.bottom = -span; sc.right = sc.top = span; sc.near = 1; sc.far = 220;
    sc.updateProjectionMatrix();
    this.scene.fog.color.copy(L.fog);
    this.scene.fog.near = Math.max(30, dist * 1.2); this.scene.fog.far = Math.max(140, dist * 3.2);
    this.dome.position.copy(target);
    // seasons and what falls
    const s = seasonAt(cal.seasonIndex, cal.seasonFrac);
    living.uSeason.value.set(...s.weights);
    living.uSnow.value = s.snow;
    const fm = this.fall.material.uniforms;
    fm.uCenter.value.set(target.x, target.y - 2, target.z);
    fm.uScale.value = Math.max(1, dist / 30);
    if (cal.seasonIndex === 3) { fm.uKind.value = 0; fm.uAmount.value = 0.5 + 0.5 * Math.sin(cal.day * 2.3) ** 2; }
    else if (cal.seasonIndex === 2) { fm.uKind.value = 1; fm.uAmount.value = 0.8; }
    else fm.uAmount.value = 0;
    this.fall.visible = fm.uAmount.value > 0.01;
    return L;
  }
}
