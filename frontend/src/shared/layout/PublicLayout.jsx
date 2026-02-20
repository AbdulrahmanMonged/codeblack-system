import { AnimatedOutlet } from "../motion/AnimatedOutlet.jsx";
import { GlobalFooter } from "./GlobalFooter.jsx";
import { GlobalNavbar } from "./GlobalNavbar.jsx";

export function PublicLayout() {
  return (
    <>
      <GlobalNavbar />
      <div className="mx-auto flex min-h-screen w-full max-w-7xl px-4 pb-8 pt-20 md:px-8">
        <div className="flex w-full flex-1 flex-col">
          <div className="flex-1">
            <AnimatedOutlet />
          </div>
          <GlobalFooter />
        </div>
      </div>
    </>
  );
}
