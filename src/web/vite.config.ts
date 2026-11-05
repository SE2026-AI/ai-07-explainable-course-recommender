import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Backend FastAPI chạy ở 127.0.0.1:8000 (xem docs/setup.md); dev server chuyển /v1 về đó.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/v1": "http://127.0.0.1:8000" },
    // Test đọc docs/architecture/api-contract.md để so mock với ví dụ của hợp đồng.
    fs: { allow: [".", "../../docs"] },
  },
  test: { environment: "jsdom", setupFiles: ["./src/test/setup.ts"] },
});
