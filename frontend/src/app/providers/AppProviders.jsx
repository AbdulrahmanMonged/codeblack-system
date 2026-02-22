import { Toast } from "@heroui/react";
import { Provider } from "react-redux";
import { PersistGate } from "redux-persist/integration/react";
import { SWRConfig } from "swr";
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
            <Toast.Provider placement="top-end" maxVisibleToasts={5} />
          </SWRConfig>
        </SessionBootstrap>
      </PersistGate>
    </Provider>
  );
}
