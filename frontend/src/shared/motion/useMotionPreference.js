import { useReducedMotion } from "framer-motion";
import { useAppSelector } from "../../app/store/hooks.js";
import { selectForceReducedMotion } from "../../app/store/slices/uiSlice.js";

export function useMotionPreference() {
  const browserReducedMotion = useReducedMotion();
  const forceReducedMotion = useAppSelector(selectForceReducedMotion);
  return Boolean(browserReducedMotion || forceReducedMotion);
}
