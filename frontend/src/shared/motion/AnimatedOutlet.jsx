import { AnimatePresence, motion } from "framer-motion";
import { Outlet, useLocation } from "react-router-dom";
import { pageMotionTransition, pageMotionVariants } from "./page-motion.js";
import { useMotionPreference } from "./useMotionPreference.js";

export function AnimatedOutlet() {
  const location = useLocation();
  const disableMotion = useMotionPreference();
  const MotionContainer = motion.div;

  const transition = disableMotion ? { duration: 0 } : pageMotionTransition;
  const variants = disableMotion
    ? { initial: { opacity: 1 }, animate: { opacity: 1 }, exit: { opacity: 1 } }
    : pageMotionVariants;

  return (
    <AnimatePresence mode="wait" initial={false}>
      <MotionContainer
        key={location.pathname}
        variants={variants}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={transition}
        className="h-full"
      >
        <Outlet />
      </MotionContainer>
    </AnimatePresence>
  );
}
