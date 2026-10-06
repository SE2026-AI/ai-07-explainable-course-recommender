/// <reference types="vitest/config" />
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const here = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // test/web lives outside this package (required repository structure).
    fs: { allow: [`${here}../..`] },
    // Live mode calls /v1 on the same origin; the dev server forwards it to the FastAPI backend.
    proxy: { "/v1": process.env.AI07_API_URL ?? "http://127.0.0.1:8000" },
  },
  test: {
    // Tests live in test/web (required repository structure), outside this package.
    root: here,
    dir: `${here}../../test/web`,
    include: ["**/*.test.{ts,tsx}"],
    environment: "jsdom",
    setupFiles: [`${here}../../test/web/setup.ts`],
    server: { deps: { inline: true } },
  },
  resolve: {
    alias: [
      { find: "@web", replacement: `${here}src` },
      // Let files in test/web resolve this package's dependencies.
      { find: /^(react|react-dom|@testing-library\/[^/]+)(\/.*)?$/, replacement: `${here}node_modules/$1$2` },
    ],
  },
});
