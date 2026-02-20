import { Provider } from "react-redux";
import { PersistGate } from "redux-persist/integration/react";
import { SWRConfig } from "swr";
import { Toaster } from "sonner";
import { persistor, store } from "../store/index.js";
import { apiFetcher } from "../../core/api/http-client.js";
import { SessionBootstrap } from "./SessionBootstrap.jsx";

const swrOptions = {
  fetcher: apiFetcher,
  revalidateOnFocus: false,
  shouldRetryOnError: false,
  keepPreviousData: true,
};

export function AppProviders({ children }) {
  return (
    <Provider store={store}>
      <PersistGate loading={null} persistor={persistor}>
        <SessionBootstrap>
          <SWRConfig value={swrOptions}>
            {children}
            <Toaster
              closeButton
              richColors
              position="top-right"
              duration={3500}
            />
          </SWRConfig>
        </SessionBootstrap>
      </PersistGate>
    </Provider>
  );
}
