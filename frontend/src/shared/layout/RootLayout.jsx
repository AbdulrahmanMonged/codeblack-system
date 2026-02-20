import { Outlet } from "react-router-dom";
import { AppBackground } from "./AppBackground.jsx";

export function RootLayout() {
  return (
    <div className="relative min-h-screen text-white">
      <AppBackground />
      <div className="relative z-10 min-h-screen">
        <Outlet />
      </div>
    </div>
  );
}
