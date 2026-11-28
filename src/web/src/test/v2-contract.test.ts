import { describe, expect, it } from "vitest";
import contract from "../../../../docs/architecture/api-contract-v2.md?raw";
import { hasUserMessage } from "../api/errors";
import examples from "../api/v2/examples.json";

describe("CONTRACT-2: v2 fixtures do not drift from PR #65", () => {
  it.each(Array.from({ length: 15 }, (_, i) => i + 1))("all JSON examples in section 6.%i", (number) => {
    const heading = `### 6.${number} `;
    const start = contract.indexOf(heading);
    expect(start).toBeGreaterThan(-1);
    const rest = contract.slice(start + heading.length);
    const end = rest.search(/\r?\n### /);
    const section = end < 0 ? rest : rest.slice(0, end);
    const expected = [...section.matchAll(/```json\r?\n([\s\S]*?)```/g)].map((m) => JSON.parse(m[1]));
    expect((examples as Record<string, unknown[]>)[`6.${number}`]).toEqual(expected);
  });
  it("every v2 error has an explicit Vietnamese message", () => {
    const section = contract.slice(contract.indexOf("## 4. Lỗi"), contract.indexOf("## 5. Danh sách"));
    const codes = [...section.matchAll(/^\| \d+ \| `([a-z_]+)` \|/gm)].map((m) => m[1]);
    expect(codes.length).toBeGreaterThanOrEqual(15);
    for (const code of codes) expect(hasUserMessage(code), code).toBe(true);
  });
});
