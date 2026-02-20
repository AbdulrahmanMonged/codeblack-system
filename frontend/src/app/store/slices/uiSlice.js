import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  sidebarOpen: false,
  forceReducedMotion: false,
};

const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    toggleSidebar(state) {
      state.sidebarOpen = !state.sidebarOpen;
    },
    openSidebar(state) {
      state.sidebarOpen = true;
    },
    closeSidebar(state) {
      state.sidebarOpen = false;
    },
    setForceReducedMotion(state, action) {
      state.forceReducedMotion = Boolean(action.payload);
    },
  },
});

export const {
  toggleSidebar,
  openSidebar,
  closeSidebar,
  setForceReducedMotion,
} = uiSlice.actions;

export const selectSidebarOpen = (state) => state.ui.sidebarOpen;
export const selectForceReducedMotion = (state) => state.ui.forceReducedMotion;

export default uiSlice.reducer;
