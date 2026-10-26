import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "../App";
import { createMockClient, type ApiClient } from "../api/client";
import { Prerequisites } from "../components/Prerequisites";

function renderApp(client: ApiClient, url = "/catalog") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <App client={client} />
    </MemoryRouter>,
  );
}

describe("App", () => {
  it("hiện algorithm_version từ /v1/meta và bảng học phần của khung", async () => {
    renderApp(createMockClient(), "/catalog?uni=HUS&curriculum=HUS-7480113QTD-2022");
    expect(await screen.findByTestId("meta")).toHaveTextContent("rule_based_weighted 1.0.0");
    const row = (await screen.findByText("MAT2505")).closest("tr")!;
    expect(within(row).getByText("Lập trình cơ bản")).toBeInTheDocument();
    expect(within(row).getByText("HUS1011")).toBeInTheDocument();
    expect(screen.getByText("Ngoại ngữ B1")).toBeInTheDocument();
  });

  it("chọn trường rồi chọn khung", async () => {
    renderApp(createMockClient());
    const [uni, curriculum] = await screen.findAllByRole("combobox");
    await screen.findByRole("option", { name: /HUS/ });
    await userEvent.selectOptions(uni, "HUS");
    await screen.findByRole("option", { name: /HUS-7460108-2022/ });
    await userEvent.selectOptions(curriculum, "HUS-7480113QTD-2022");
    expect(await screen.findByText("MAT2505")).toBeInTheDocument();
  });

  it("kịch bản rỗng có thông báo, không phải trang trắng", async () => {
    renderApp(createMockClient("empty"), "/catalog?uni=HUS&curriculum=C");
    expect(await screen.findByText("Hệ thống chưa có trường nào.")).toBeInTheDocument();
    expect(await screen.findByText("Khung này chưa có học phần nào.")).toBeInTheDocument();
  });

  it("kịch bản lỗi hiện câu tiếng Việt và mã lỗi", async () => {
    renderApp(createMockClient("error"), "/catalog?uni=XX&curriculum=C");
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.map((a) => a.textContent).join(" ")).toContain("university_not_found");
    expect(screen.getAllByText(/Không tìm thấy chương trình đào tạo/).length).toBeGreaterThan(0);
  });

  it("trang vấn đề dữ liệu", async () => {
    renderApp(createMockClient(), "/data-issues");
    expect(await screen.findByText(/Một số điều kiện tiên quyết dùng mã không thuộc CTĐT/)).toBeInTheDocument();
  });
});

describe("Prerequisites (§4.2)", () => {
  const text = (groups: string[][]) => render(<Prerequisites groups={groups} />).container.textContent;

  it("nhiều nhóm nối bằng VÀ", () => {
    expect(text([["MAT2400"], ["MAT3533"]])).toBe("MAT2400 và MAT3533");
  });
  it("nhiều mã trong một nhóm nối bằng HOẶC, không làm phẳng thành VÀ", () => {
    expect(text([["CS101", "MAT2505"]])).toBe("CS101 hoặc MAT2505");
  });
  it("kết hợp cả hai thì gom nhóm bằng ngoặc", () => {
    expect(text([["A", "B"], ["C"]])).toBe("(A hoặc B) và C");
  });
  it("danh sách rỗng là không có tiên quyết", () => {
    expect(text([])).toBe("Không có");
  });
});
