import { create } from "zustand";

type UiState = {
  mobileMenuOpen: boolean;
  filterDrawerOpen: boolean;
  chatOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
  setFilterDrawerOpen: (open: boolean) => void;
  setChatOpen: (open: boolean) => void;
};

export const useUiStore = create<UiState>((set) => ({
  mobileMenuOpen: false,
  filterDrawerOpen: false,
  chatOpen: false,
  setMobileMenuOpen: (mobileMenuOpen) => set({ mobileMenuOpen }),
  setFilterDrawerOpen: (filterDrawerOpen) => set({ filterDrawerOpen }),
  setChatOpen: (chatOpen) => set({ chatOpen }),
}));
