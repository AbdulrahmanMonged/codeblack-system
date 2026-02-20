export function GlobalFooter({ embedded = false }) {
  return (
    <footer
      className={
        embedded
          ? "border-t border-white/10 px-0 py-4 text-center text-xs text-[#b8ac8a]"
          : "relative z-10 mt-10 border-t border-white/10 px-4 py-6 text-center text-xs text-[#b8ac8a]"
      }
    >
      CodeBlack Operations Center • Recruitment and internal operations platform.
    </footer>
  );
}
