// stores/useObjectsStore.ts
import { create } from "zustand";

export type ObjectStatus = "Не начато" | "В работе" | "Выполнено";

export interface IObject {
  name: string;
  status: string;        // оставил string — если хочешь строго как у субобъектов, поменяй на ObjectStatus
  object_id: number;
}

export interface ISubObject {
  name: string;
  status_inspector: ObjectStatus;
  status_contractor: ObjectStatus;
  status_admin: ObjectStatus;
  prescription_info: string;
  subobject_id: number;
  object_id: number;
}

interface IObjectState {
  activeObject: IObject | null;
  activeSubObject: ISubObject | null;
  objects: IObject[];
  subObjects: ISubObject[];

  setObjects: (objects: IObject[]) => void;
  clearObjects: () => void;
  setActiveObject: (obj: IObject) => void;

  setSubObjects: (subObjects: ISubObject[]) => void;
  clearSubObjects: () => void;
  setActiveSubObject: (sub: ISubObject | null) => void;
}

export const useObjectsStore = create<IObjectState>((set) => ({
  activeObject: null,
  activeSubObject: null,

  objects: [],
  subObjects: [],

  setObjects: (objects) => set({ objects }),
  clearObjects: () =>
    set({ objects: [], activeObject: null, subObjects: [], activeSubObject: null }),

  setActiveObject: (obj) =>
    set({
      activeObject: obj,
      activeSubObject: null,
      subObjects: [],
    }),

  setSubObjects: (subObjects) => set({ subObjects }),
  clearSubObjects: () => set({ subObjects: [], activeSubObject: null }),

  setActiveSubObject: (sub) => set({ activeSubObject: sub }),
}));
