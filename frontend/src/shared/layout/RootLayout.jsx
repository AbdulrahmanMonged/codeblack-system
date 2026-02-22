import { AnimatePresence, motion } from "framer-motion";
import { Outlet, useLocation } from "react-router-dom";
import { useMotionPreference } from "../motion/useMotionPreference.js";
import { AppBackground } from "./AppBackground.jsx";

const ROOT_LAYOUT_TRANSITION = {
  duration: 0.22,
  ease: [0.22, 1, 0.36, 1],
};

const ROOT_LAYOUT_VARIANTS = {
  initial: { opacity: 0, y: 10, filter: "blur(4px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  exit: { opacity: 0, y: -8, filter: "blur(4px)" },
};

const PUBLIC_PATHS = new Set([
  "/",
  "/auth/callback",
  "/applications/new",
  "/applications/eligibility",
  "/blacklist/removal-request",
  "/roster-public",
]);

function getLayoutKey(pathname) {
  if (pathname.startsWith("/verify-account")) {
    return "verify";
  }
  if (PUBLIC_PATHS.has(pathname)) {
    return "public";
  }
  return "protected";
}

export function RootLayout() {
  const location = useLocation();
  const disableMotion = useMotionPreference();

  const transition = disableMotion ? { duration: 0 } : ROOT_LAYOUT_TRANSITION;
  const variants = disableMotion
    ? { initial: { opacity: 1 }, animate: { opacity: 1 }, exit: { opacity: 1 } }
    : ROOT_LAYOUT_VARIANTS;

  return (
    <div className="relative min-h-screen text-white">
      <AppBackground />
      <div className="relative z-10 min-h-screen">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={getLayoutKey(location.pathname)}
            variants={variants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={transition}
            className="min-h-screen"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
