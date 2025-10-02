// stores/useUserStore.ts
import { create } from "zustand";

export interface IUser {
  user_id: number;
  name: string;
  role: string;
}

interface IUserState {
  user: IUser;
  setUser: (user: IUser) => void;
  updateUser: (patch: Partial<IUser>) => void;
  resetUser: () => void;
}

const getInitialUser = (): IUser => ({
  user_id: -1,
  name: "",
  role: "",
});

export const useUserStore = create<IUserState>((set) => ({
  user: getInitialUser(),

  setUser: (user) => set(() => ({ user })),

  updateUser: (patch) =>
    set((state) => ({ user: { ...state.user, ...patch } })),

  resetUser: () => set(() => ({ user: getInitialUser() })),
}));
