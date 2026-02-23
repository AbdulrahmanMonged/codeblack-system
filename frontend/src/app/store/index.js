import { combineReducers, configureStore } from "@reduxjs/toolkit";
import {
  FLUSH,
  PAUSE,
  PERSIST,
  PURGE,
  REGISTER,
  REHYDRATE,
  persistReducer,
  persistStore,
} from "redux-persist";
import storageModule from "redux-persist/lib/storage";
import sessionReducer from "./slices/sessionSlice.js";
import uiReducer from "./slices/uiSlice.js";

const noopStorage = {
  getItem: () => Promise.resolve(null),
  setItem: (_key, value) => Promise.resolve(value),
  removeItem: () => Promise.resolve(),
};

const storage =
  storageModule && typeof storageModule.getItem === "function"
    ? storageModule
    : storageModule?.default && typeof storageModule.default.getItem === "function"
      ? storageModule.default
      : noopStorage;

const rootReducer = combineReducers({
  session: sessionReducer,
  ui: uiReducer,
});

const persistConfig = {
  key: "codeblack-frontend",
  version: 1,
  storage,
  whitelist: ["ui"],
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
      },
    }),
});

export const persistor = persistStore(store);
