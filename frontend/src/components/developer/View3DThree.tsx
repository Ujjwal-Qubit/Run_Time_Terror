import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { Box, RefreshCw } from 'lucide-react';
import type { VisualizationPacket } from '../../types';
import { VideoPlayer2D } from './VideoPlayer2D';
import { TargetLock } from './TargetLock';
import { hasTargetLock } from './targetLockState';

interface View3DThreeProps {
  packet: VisualizationPacket | null;
}

export const View3DThree: React.FC<View3DThreeProps> = ({ packet }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  
  // Dynamic 3D Objects
  const frustumGroupRef = useRef<THREE.Group | null>(null);
  const targetMeshRef = useRef<THREE.Mesh | null>(null);
  const lockRingRef = useRef<THREE.Mesh | null>(null);
  const losLineRef = useRef<THREE.Line | null>(null);
  const breadcrumbLineRef = useRef<THREE.Line | null>(null);
  const breadcrumbPointsRef = useRef<THREE.Vector3[]>([]);

  // Orbit control state
  const isDraggingRef = useRef<boolean>(false);
  const isRightDraggingRef = useRef<boolean>(false);
  const mousePosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const sphericalRef = useRef<{ radius: number; theta: number; phi: number }>({
    radius: 350,
    theta: Math.PI / 4,
    phi: Math.PI / 3,
  });
  const targetPosRef = useRef<THREE.Vector3>(new THREE.Vector3(0, 0, 0));

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x06090e);
    sceneRef.current = scene;

    const width = container.clientWidth || 640;
    const height = container.clientHeight || 480;

    // 2. Camera setup
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 3000);
    cameraRef.current = camera;
    updateCameraPosition();

    // 3. Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    rendererRef.current = renderer;
    container.appendChild(renderer.domElement);

    // 4. Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);
    const dirLight = new THREE.DirectionalLight(0x00d2ff, 1.2);
    dirLight.position.set(200, 400, 200);
    scene.add(dirLight);

    // 5. Ground Grid (400x400)
    const gridHelper = new THREE.GridHelper(400, 40, 0x00d2ff, 0x1e293b);
    gridHelper.position.y = -20;
    scene.add(gridHelper);

    // 6. Coordinate Axes
    const axesHelper = new THREE.AxesHelper(60);
    axesHelper.position.set(0, -19.9, 0);
    scene.add(axesHelper);

    // 7. Terminal Pedestal
    const pedestalGeo = new THREE.CylinderGeometry(15, 20, 20, 32);
    const pedestalMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      roughness: 0.4,
      metalness: 0.8,
    });
    const pedestal = new THREE.Mesh(pedestalGeo, pedestalMat);
    pedestal.position.set(0, -10, 0);
    scene.add(pedestal);

    // 8. Dynamic Camera Frustum (PTZ Gimbal)
    const frustumGroup = new THREE.Group();
    frustumGroup.position.set(0, 0, 0);

    // Camera housing sits behind the optical origin; its lens faces local +Z.
    const housing = new THREE.Mesh(new THREE.BoxGeometry(18, 12, 14), new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.7, roughness: 0.3 }));
    housing.position.z = -12;
    frustumGroup.add(housing);
    const lens = new THREE.Mesh(new THREE.CylinderGeometry(5, 6, 5, 24), new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.8, roughness: 0.2 }));
    lens.rotation.x = Math.PI / 2;
    lens.position.z = -2.5;
    frustumGroup.add(lens);
    const glass = new THREE.Mesh(new THREE.CircleGeometry(4, 24), new THREE.MeshBasicMaterial({ color: 0x00d2ff, side: THREE.DoubleSide }));
    glass.position.z = 0.1;
    frustumGroup.add(glass);
    const viewfinder = new THREE.Mesh(new THREE.BoxGeometry(7, 4, 6), new THREE.MeshStandardMaterial({ color: 0x94a3b8 }));
    viewfinder.position.set(0, 8, -12);
    frustumGroup.add(viewfinder);

    // Frustum pyramid geometry
    const pyramidGeo = new THREE.BufferGeometry();
    const fl = 60;
    const fw = 30;
    const fh = 22.5;
    const vertices = new Float32Array([
      // Apex to corners
      0, 0, 0,  -fw, fh, fl,
      0, 0, 0,   fw, fh, fl,
      0, 0, 0,   fw, -fh, fl,
      0, 0, 0,  -fw, -fh, fl,
      // Rectangular base
      -fw, fh, fl,  fw, fh, fl,
      fw, fh, fl,   fw, -fh, fl,
      fw, -fh, fl, -fw, -fh, fl,
      -fw, -fh, fl, -fw, fh, fl,
    ]);
    pyramidGeo.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
    const frustumMat = new THREE.LineBasicMaterial({ color: 0x00d2ff, linewidth: 2 });
    const frustumLines = new THREE.LineSegments(pyramidGeo, frustumMat);
    frustumGroup.add(frustumLines);

    // Optical Axis Ray (Yellow dashed)
    const rayGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 0, 250),
    ]);
    const rayMat = new THREE.LineDashedMaterial({
      color: 0xfacc15,
      dashSize: 6,
      gapSize: 4,
    });
    const rayLine = new THREE.Line(rayGeo, rayMat);
    rayLine.computeLineDistances();
    frustumGroup.add(rayLine);

    scene.add(frustumGroup);
    frustumGroupRef.current = frustumGroup;

    // 9. Target Beacon (Red Sphere)
    const targetGeo = new THREE.SphereGeometry(6, 16, 16);
    const targetMat = new THREE.MeshStandardMaterial({
      color: 0xef4444,
      emissive: 0xff0000,
      emissiveIntensity: 0.6,
    });
    const targetMesh = new THREE.Mesh(targetGeo, targetMat);
    targetMesh.position.set(0, 40, 150);
    scene.add(targetMesh);
    targetMeshRef.current = targetMesh;
    const lockRing = new THREE.Mesh(new THREE.RingGeometry(10, 11, 48), new THREE.MeshBasicMaterial({ color: 0x34d399, side: THREE.DoubleSide, depthTest: false }));
    lockRing.visible = false;
    scene.add(lockRing);
    lockRingRef.current = lockRing;

    // 10. Line-of-Sight (LOS) Beam (Semi-transparent green laser)
    const losGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 40, 150),
    ]);
    const losMat = new THREE.LineBasicMaterial({
      color: 0x10b981,
      transparent: true,
      opacity: 0.7,
      linewidth: 2,
    });
    const losLine = new THREE.Line(losGeo, losMat);
    scene.add(losLine);
    losLineRef.current = losLine;

    // 11. Historical Breadcrumbs Trail (Orange)
    const breadcrumbGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 0, 0),
    ]);
    const breadcrumbMat = new THREE.LineBasicMaterial({
      color: 0xf97316,
      transparent: true,
      opacity: 0.8,
    });
    const breadcrumbLine = new THREE.Line(breadcrumbGeo, breadcrumbMat);
    scene.add(breadcrumbLine);
    breadcrumbLineRef.current = breadcrumbLine;

    // Render loop
    let animationId: number;
    const animate = () => {
      animationId = requestAnimationFrame(animate);
      lockRing.quaternion.copy(camera.quaternion);
      renderer.render(scene, camera);
    };
    animate();

    // Resize handler: the tab content may change size without a window resize.
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const w = Math.max(1, container.clientWidth);
      const h = Math.max(1, container.clientHeight);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationId);
      resizeObserver.disconnect();
      window.removeEventListener('resize', handleResize);
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line) {
          object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach((material) => material.dispose());
        }
      });
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  const updateCameraPosition = () => {
    if (!cameraRef.current) return;
    const { radius, theta, phi } = sphericalRef.current;
    const x = radius * Math.sin(phi) * Math.sin(theta) + targetPosRef.current.x;
    const y = radius * Math.cos(phi) + targetPosRef.current.y;
    const z = radius * Math.sin(phi) * Math.cos(theta) + targetPosRef.current.z;

    cameraRef.current.position.set(x, y, z);
    cameraRef.current.lookAt(targetPosRef.current);
  };

  // Sync with packet updates
  useEffect(() => {
    if (!packet) {
      if (lockRingRef.current) lockRingRef.current.visible = false;
      if (targetMeshRef.current) targetMeshRef.current.visible = false;
      if (losLineRef.current) losLineRef.current.visible = false;
      if (breadcrumbLineRef.current) breadcrumbLineRef.current.visible = false;
      breadcrumbPointsRef.current = [];
      frustumGroupRef.current?.rotation.set(0, 0, 0);
      return;
    }

    // 1. Orient PTZ Frustum using pan and tilt
    if (frustumGroupRef.current) {
      const panRad = THREE.MathUtils.degToRad(-packet.pan_angle_deg);
      const tiltRad = THREE.MathUtils.degToRad(packet.tilt_angle_deg);

      frustumGroupRef.current.rotation.set(0, 0, 0);
      frustumGroupRef.current.rotateY(panRad);
      frustumGroupRef.current.rotateX(-tiltRad);
    }

    // 2. Compute 3D target coordinates from tracking centroid or ground truth
    const dist = 180;
    let targetX = 0;
    let targetY = 30;
    let targetZ = dist;

    if (packet.estimated_centroid || packet.ground_truth) {
      const coord = packet.estimated_centroid || packet.ground_truth!;
      const resW = packet.resolution?.width || 640;
      const resH = packet.resolution?.height || 480;

      // Convert observed pixel offset to angular line-of-sight, then combine
      // it with the simulated gimbal pose. Keep the displayed range normalized:
      // this 2D simulation does not provide physical beacon range/depth.
      const hFovRad = THREE.MathUtils.degToRad(packet.camera_fov);
      const vFovRad = hFovRad * resH / resW;
      const panRad = THREE.MathUtils.degToRad(-packet.pan_angle_deg) + ((coord.x - resW / 2) / resW) * hFovRad;
      const tiltRad = THREE.MathUtils.degToRad(packet.tilt_angle_deg) - ((coord.y - resH / 2) / resH) * vFovRad;
      targetX = dist * Math.sin(panRad) * Math.cos(tiltRad);
      targetY = dist * Math.sin(tiltRad);
      targetZ = dist * Math.cos(panRad) * Math.cos(tiltRad);
    }

    const currentPos = new THREE.Vector3(targetX, targetY, targetZ);

    // Update target mesh position
    if (targetMeshRef.current) {
      targetMeshRef.current.visible = !!(packet.estimated_centroid || packet.ground_truth);
      targetMeshRef.current.position.copy(currentPos);
    }
    const locked = hasTargetLock(packet);
    if (lockRingRef.current) {
      lockRingRef.current.visible = locked;
      lockRingRef.current.position.copy(currentPos);
    }

    // Update LOS laser beam
    if (losLineRef.current) {
      losLineRef.current.visible = locked;
      const pts = [new THREE.Vector3(0, 0, 0), currentPos];
      losLineRef.current.geometry.setFromPoints(pts);
    }

    // Update historical breadcrumb path (keep last 60 frames)
    if (breadcrumbLineRef.current) {
      breadcrumbLineRef.current.visible = !!(packet.estimated_centroid || packet.ground_truth);
      const pts = breadcrumbPointsRef.current;
      pts.push(currentPos.clone());
      if (pts.length > 60) {
        pts.shift();
      }
      if (pts.length >= 2) {
        breadcrumbLineRef.current.geometry.setFromPoints(pts);
      }
    }
  }, [packet]);

  // Mouse interaction handlers (Orbit, Pan, Zoom)
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) isDraggingRef.current = true;
    if (e.button === 2) isRightDraggingRef.current = true;
    mousePosRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDraggingRef.current && !isRightDraggingRef.current) return;

    const dx = e.clientX - mousePosRef.current.x;
    const dy = e.clientY - mousePosRef.current.y;
    mousePosRef.current = { x: e.clientX, y: e.clientY };

    if (isDraggingRef.current) {
      // Left click: Orbit
      sphericalRef.current.theta -= dx * 0.005;
      sphericalRef.current.phi = Math.max(0.1, Math.min(Math.PI / 2 - 0.05, sphericalRef.current.phi - dy * 0.005));
    } else if (isRightDraggingRef.current) {
      // Right click: Pan
      targetPosRef.current.x -= dx * 0.2;
      targetPosRef.current.y += dy * 0.2;
    }

    updateCameraPosition();
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
    isRightDraggingRef.current = false;
  };

  const handleWheel = (e: React.WheelEvent) => {
    sphericalRef.current.radius = Math.max(80, Math.min(800, sphericalRef.current.radius + e.deltaY * 0.5));
    updateCameraPosition();
  };

  const resetView = () => {
    sphericalRef.current = { radius: 350, theta: Math.PI / 4, phi: Math.PI / 3 };
    targetPosRef.current.set(0, 0, 0);
    breadcrumbPointsRef.current = [];
    updateCameraPosition();
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Viewport Header */}
      <div style={{
        padding: '8px 14px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '12px',
        background: 'rgba(10, 15, 25, 0.6)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#00d2ff', fontWeight: 600 }}>
          <Box className="w-4 h-4" />
          <span>3D Orbital Geometry & PTZ Gimbal Frustum</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Drag: Orbit | Right-Drag: Pan | Scroll: Zoom
          </span>
          <button
            onClick={resetView}
            className="btn btn-secondary"
            style={{ fontSize: '11px', padding: '4px 8px' }}
            title="Reset Camera View"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset View</span>
          </button>
        </div>
      </div>

      {/* 3D Canvas Area */}
      <div style={{ flex: 1, minHeight: 0, position: 'relative', overflow: 'hidden' }}>
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        onContextMenu={(e) => e.preventDefault()}
        style={{
          flex: 1,
          width: '100%',
          height: '100%',
          cursor: 'grab',
          position: 'relative'
        }}
      />
      <div style={{ position: 'absolute', top: '12px', left: '12px', pointerEvents: 'none' }}><TargetLock packet={packet} /></div>
      <div aria-label="Live 2D sensor inset" style={{ position: 'absolute', bottom: '12px', right: '12px', width: 'clamp(160px, 32%, 300px)', maxWidth: '48%', height: '45%', maxHeight: '245px', boxShadow: '0 6px 24px rgba(0,0,0,0.6)', borderRadius: '8px' }}>
        <VideoPlayer2D packet={packet} compact />
      </div>
      </div>
    </div>
  );
};
