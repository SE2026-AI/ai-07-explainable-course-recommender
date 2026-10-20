// Mock phải là nguyên văn ví dụ của api-contract.md: đọc lại file hợp đồng và so từng khối JSON.
import { describe, expect, it } from "vitest";
import contract from "../../../../docs/architecture/api-contract.md?raw";
import { SERVER_ERROR_CODES, hasUserMessage } from "../api/errors";

const fixtures = import.meta.glob("../api/mocks/contract/*.json", { eager: true, import: "default" });
const fixture = (name: string) => fixtures[`../api/mocks/contract/${name}.json`];

/** Các khối ```json dưới một tiêu đề của hợp đồng, theo thứ tự xuất hiện. */
function examples(heading: string): unknown[] {
  const start = contract.indexOf(heading);
  if (start < 0) throw new Error(`Không thấy mục ${heading} trong api-contract.md`);
  const rest = contract.slice(start + heading.length);
  const end = rest.search(/\n#{2,3} /);
  const section = end < 0 ? rest : rest.slice(0, end);
  return [...section.matchAll(/```json\n([\s\S]*?)```/g)].map((m) => JSON.parse(m[1]));
}

describe("mock lấy nguyên văn từ api-contract.md", () => {
  it.each([
    ["## 5. Lỗi", ["error-student-not-found"]],
    ["### 6.1 ", ["meta"]],
    ["### 6.2 ", ["curriculum"]],
    ["### 6.3 ", ["curriculum-courses"]],
    ["### 6.4 ", ["profile"]],
    ["### 6.5 ", ["course-status"]],
    ["### 6.6 ", ["recommendations-request", "recommendations"]],
    ["### 6.7 ", ["plan-check-request", "plan-check"]],
    ["### 6.8 ", ["data-issues"]],
  ])("%s", (heading, names) => {
    expect(names.map(fixture)).toEqual(examples(heading));
  });

  it("có câu tiếng Việt cho mọi mã lỗi trong bảng §5", () => {
    const section = contract.slice(contract.indexOf("## 5. Lỗi"), contract.indexOf("## 6. Endpoint"));
    const codes = [...section.matchAll(/^\| [^|]+ \| `([a-z_]+)` \|/gm)].map((m) => m[1]).filter((c) => c !== "code"); // bỏ dòng tiêu đề
    expect(codes).toHaveLength(11);
    expect([...codes].sort()).toEqual([...SERVER_ERROR_CODES].sort());
    for (const code of codes) expect(hasUserMessage(code), code).toBe(true);
  });
});
