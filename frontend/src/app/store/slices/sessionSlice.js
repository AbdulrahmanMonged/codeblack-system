import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  status: "unknown",
  user: null,
  roleIds: [],
  permissions: [],
  isOwner: false,
  isVerified: false,
};

const sessionSlice = createSlice({
  name: "session",
  initialState,
  reducers: {
    hydrationStarted(state) {
      state.status = "hydrating";
    },
    hydrationCompleted(state, action) {
      const payload = action.payload ?? {};
      state.status = "authenticated";
      state.user = payload.user ?? null;
      state.roleIds = payload.roleIds ?? [];
      state.permissions = payload.permissions ?? [];
      state.isOwner = Boolean(payload.isOwner);
      state.isVerified = Boolean(payload.isVerified ?? payload.user?.isVerified);
    },
    hydrationFailed(state) {
      state.status = "anonymous";
      state.user = null;
      state.roleIds = [];
      state.permissions = [];
      state.isOwner = false;
      state.isVerified = false;
    },
    clearSession(state) {
      state.status = "anonymous";
      state.user = null;
      state.roleIds = [];
      state.permissions = [];
      state.isOwner = false;
      state.isVerified = false;
    },
  },
});

export const {
  hydrationStarted,
  hydrationCompleted,
  hydrationFailed,
  clearSession,
} = sessionSlice.actions;

export const selectSessionStatus = (state) => state.session.status;
export const selectCurrentUser = (state) => state.session.user;
export const selectPermissions = (state) => state.session.permissions;
export const selectIsOwner = (state) => state.session.isOwner;
export const selectIsVerified = (state) => state.session.isVerified;

export default sessionSlice.reducer;
