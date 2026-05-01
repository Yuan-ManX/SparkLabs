import * as THREE from 'three';
import type { SceneNode } from '../store/editorStore';

export interface EntityMeshEntry {
  entityId: string;
  name: string;
  mesh: THREE.Object3D;
  entityType: string;
  transform: { position: THREE.Vector3; rotation: THREE.Euler; scale: THREE.Vector3 };
}

class SceneBridge {
  private _meshes: Map<string, EntityMeshEntry> = new Map();
  private _listeners: Array<() => void> = [];

  subscribe(listener: () => void): () => void {
    this._listeners.push(listener);
    return () => { this._listeners = this._listeners.filter((l) => l !== listener); };
  }

  private notify() {
    this._listeners.forEach((l) => l());
  }

  buildFromNodes(nodes: SceneNode[]): EntityMeshEntry[] {
    const entries: EntityMeshEntry[] = [];
    const existingIds = new Set(this._meshes.keys());

    const traverse = (list: SceneNode[], parentTransform?: THREE.Matrix4) => {
      for (const node of list) {
        existingIds.delete(node.id);

        if (node.type === 'entity') {
          let entry = this._meshes.get(node.id);
          if (!entry) {
            const mesh = this.createMeshForEntity(node);
            entry = {
              entityId: node.id,
              name: node.name,
              mesh,
              entityType: this.inferEntityType(node),
              transform: {
                position: new THREE.Vector3(0, 0, 0),
                rotation: new THREE.Euler(0, 0, 0),
                scale: new THREE.Vector3(1, 1, 1),
              },
            };
            this._meshes.set(node.id, entry);
          }
          entries.push(entry);
        } else if (node.type === 'group') {
          traverse(node.children, undefined);
        }
      }
    };

    traverse(nodes);

    for (const id of existingIds) {
      const entry = this._meshes.get(id);
      if (entry) {
        this.disposeMesh(entry.mesh);
        this._meshes.delete(id);
      }
    }

    this.notify();
    return entries;
  }

  updateEntityTransform(entityId: string, position?: [number, number, number], rotation?: [number, number, number], scale?: [number, number, number]) {
    const entry = this._meshes.get(entityId);
    if (!entry) return;

    if (position) {
      entry.transform.position.set(position[0], position[1], position[2]);
      entry.mesh.position.copy(entry.transform.position);
    }
    if (rotation) {
      entry.transform.rotation.set(rotation[0], rotation[1], rotation[2]);
      entry.mesh.rotation.copy(entry.transform.rotation);
    }
    if (scale) {
      entry.transform.scale.set(scale[0], scale[1], scale[2]);
      entry.mesh.scale.copy(entry.transform.scale);
    }

    this.notify();
  }

  getEntityMesh(entityId: string): THREE.Object3D | undefined {
    return this._meshes.get(entityId)?.mesh;
  }

  getAllMeshes(): EntityMeshEntry[] {
    return Array.from(this._meshes.values());
  }

  disposeAll() {
    this._meshes.forEach((entry) => this.disposeMesh(entry.mesh));
    this._meshes.clear();
  }

  private createMeshForEntity(node: SceneNode): THREE.Object3D {
    const nameLower = node.name.toLowerCase();

    const isCamera = nameLower.includes('camera');
    const isLight = nameLower.includes('light') || nameLower.includes('sun');
    const isPlayer = nameLower.includes('player');
    const isNPC = nameLower.includes('npc') || nameLower.includes('agent');
    const isTerrain = nameLower.includes('terrain') || nameLower.includes('ground');
    const isCore = nameLower.includes('core') || nameLower.includes('ai');

    if (isCore) {
      const geo = new THREE.IcosahedronGeometry(0.8, 1);
      const mat = new THREE.MeshStandardMaterial({ color: 0xf97316, emissive: 0xf97316, emissiveIntensity: 0.3, roughness: 0.3, metalness: 0.7 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.castShadow = true;
      mesh.position.set(0, 1.5, 0);
      return mesh;
    }

    if (isCamera) {
      const geo = new THREE.ConeGeometry(0.15, 0.3, 4);
      const mat = new THREE.MeshStandardMaterial({ color: 0x4ade80, roughness: 0.3, metalness: 0.7 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.rotation.x = Math.PI / 4;
      return mesh;
    }

    if (isLight) {
      const geo = new THREE.SphereGeometry(0.3, 16, 16);
      const mat = new THREE.MeshStandardMaterial({ color: 0xfbbf24, emissive: 0xfbbf24, emissiveIntensity: 1.0 });
      const mesh = new THREE.Mesh(geo, mat);
      return mesh;
    }

    if (isPlayer) {
      const group = new THREE.Group();
      const bodyGeo = new THREE.BoxGeometry(0.4, 0.6, 0.3);
      const bodyMat = new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.5, metalness: 0.3 });
      const body = new THREE.Mesh(bodyGeo, bodyMat);
      body.position.y = 0.5;
      body.castShadow = true;
      group.add(body);

      const headGeo = new THREE.SphereGeometry(0.18, 16, 16);
      const headMat = new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.5, metalness: 0.3 });
      const head = new THREE.Mesh(headGeo, headMat);
      head.position.y = 1.0;
      head.castShadow = true;
      group.add(head);
      return group;
    }

    if (isNPC) {
      const geo = new THREE.CapsuleGeometry(0.2, 0.5, 8, 16);
      const mat = new THREE.MeshStandardMaterial({ color: 0xc084fc, emissive: 0xc084fc, emissiveIntensity: 0.15, roughness: 0.4, metalness: 0.5 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.castShadow = true;
      return mesh;
    }

    if (isTerrain) {
      const geo = new THREE.BoxGeometry(4, 0.5, 4);
      const mat = new THREE.MeshStandardMaterial({ color: 0x2d5a27, roughness: 0.8, metalness: 0.1 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      return mesh;
    }

    const geo = new THREE.BoxGeometry(0.6, 0.6, 0.6);
    const mat = new THREE.MeshStandardMaterial({ color: 0x60a5fa, roughness: 0.6 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.castShadow = true;
    return mesh;
  }

  private inferEntityType(node: SceneNode): string {
    const nl = node.name.toLowerCase();
    if (nl.includes('camera')) return 'camera';
    if (nl.includes('light') || nl.includes('sun')) return 'light';
    if (nl.includes('player')) return 'character';
    if (nl.includes('npc') || nl.includes('agent')) return 'npc';
    if (nl.includes('terrain') || nl.includes('ground')) return 'terrain';
    if (nl.includes('core') || nl.includes('ai')) return 'ai_core';
    return 'entity';
  }

  private disposeMesh(obj: THREE.Object3D) {
    obj.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.geometry.dispose();
        if (Array.isArray(child.material)) {
          child.material.forEach((m) => m.dispose());
        } else {
          child.material.dispose();
        }
      }
    });
  }
}

export const sceneBridge = new SceneBridge();
