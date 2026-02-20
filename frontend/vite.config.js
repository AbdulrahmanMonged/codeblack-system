
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const publicDir = fileURLToPath(new URL("../codeblack-media", import.meta.url));
const srcDir = fileURLToPath(new URL("./src", import.meta.url));

export default defineConfig({
  publicDir,
  build: {
    chunkSizeWarningLimit: 1500,
  },
  resolve: {
    alias: {
      "@": srcDir,
    },
  },
  plugins: [
    react({
      babel: {
        plugins: [["babel-plugin-react-compiler"]],
      },

    }),
    tailwindcss(),
  ],
});
