export const pageMotionVariants = {
  initial: { opacity: 0, y: 16, filter: "blur(6px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  exit: { opacity: 0, y: -12, filter: "blur(6px)" },
};

export const pageMotionTransition = {
  duration: 0.28,
  ease: [0.22, 1, 0.36, 1],
};
