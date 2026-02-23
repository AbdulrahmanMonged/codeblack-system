import { AnimatePresence, motion } from "framer-motion";
import { useMemo } from "react";
import { useLocation } from "react-router-dom";
import { resolveMediaUrl } from "../utils/media.js";
import { useMotionPreference } from "../motion/useMotionPreference.js";

const MAIN_BANNERS = [
  {
    matches: (pathname) =>
      pathname === "/dashboard" ||
      pathname === "/verify-account" ||
      pathname.startsWith("/admin") ||
      pathname.startsWith("/config"),
    src: resolveMediaUrl("/main/REDACTED-glitched-banner.gif"),
  },
  {
    matches: (pathname) => pathname.startsWith("/applications"),
    src: resolveMediaUrl("/main/application-banner.png"),
  },
  {
    matches: (pathname) => pathname.startsWith("/roster"),
    src: resolveMediaUrl("/main/hall-of-fame-roster-banner.png"),
  },
  {
    matches: (pathname) => pathname.startsWith("/activities") || pathname.startsWith("/vacations"),
    src: resolveMediaUrl("/main/gathering-for-patrol.png"),
  },
];

const RANDOM_BACKGROUNDS = [
  resolveMediaUrl("/random/capturing-drug-criminal-2.png"),
  resolveMediaUrl("/random/capturing-drug-criminal.png"),
  resolveMediaUrl("/random/oneline.png"),
  resolveMediaUrl("/random/patrolling.png"),
  resolveMediaUrl("/random/standing-next-to-each-other-2.png"),
  resolveMediaUrl("/random/standing-next-to-each-other-3.png"),
  resolveMediaUrl("/random/standing-next-to-each-other.png"),
];

function hashPath(pathname) {
  let hash = 0;
  for (let i = 0; i < pathname.length; i += 1) {
    hash = (hash << 5) - hash + pathname.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function resolveBanner(pathname) {
  const matched = MAIN_BANNERS.find((entry) => entry.matches(pathname));
  if (matched) {
    return matched.src;
  }

  const index = hashPath(pathname || "/") % RANDOM_BACKGROUNDS.length;
  return RANDOM_BACKGROUNDS[index];
}

export function AppBackground() {
  const location = useLocation();
  const disableMotion = useMotionPreference();
  const activeBanner = useMemo(
    () => resolveBanner(location.pathname),
    [location.pathname],
  );

  const MotionImage = motion.img;

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {disableMotion ? (
        <img
          src={activeBanner}
          alt=""
          aria-hidden="true"
          className="h-full w-full object-cover opacity-[0.42]"
        />
      ) : (
        <AnimatePresence mode="wait" initial={false}>
          <MotionImage
            key={activeBanner}
            src={activeBanner}
            alt=""
            aria-hidden="true"
            className="h-full w-full object-cover"
            initial={{ opacity: 0, scale: 1.03 }}
            animate={{ opacity: 0.42, scale: 1 }}
            exit={{ opacity: 0, scale: 1.02 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          />
        </AnimatePresence>
      )}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,188,72,0.22),transparent_42%)]" />
      <div className="absolute inset-0 bg-[linear-gradient(120deg,rgba(10,12,18,0.9),rgba(10,12,18,0.58),rgba(10,12,18,0.82))]" />
      <div className="absolute inset-0 cb-grid-overlay" />
    </div>
  );
}
