import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useAppDispatch } from "../../app/store/hooks.js";
import { closeSidebar } from "../../app/store/slices/uiSlice.js";
import { AnimatedOutlet } from "../motion/AnimatedOutlet.jsx";
import { AppSidebar } from "./AppSidebar.jsx";
import { GlobalFooter } from "./GlobalFooter.jsx";
import { GlobalNavbar } from "./GlobalNavbar.jsx";

export function AppShell() {
  const dispatch = useAppDispatch();
  const location = useLocation();

  useEffect(() => {
    dispatch(closeSidebar());
  }, [dispatch, location.pathname]);

  return (
    <div className="flex h-screen w-full">
      <AppSidebar />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col md:ml-0">
        <div className="px-3 pt-3 md:px-6 md:pt-4">
          <GlobalNavbar embedded />
        </div>
        <main className="flex-1 overflow-y-auto px-3 py-4 md:px-6 md:py-6">
          <AnimatedOutlet />
        </main>
        <div className="px-3 pb-3 md:px-6 md:pb-4">
          <GlobalFooter embedded />
        </div>
      </div>
    </div>
  );
}
