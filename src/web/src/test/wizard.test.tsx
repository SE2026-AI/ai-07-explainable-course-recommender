import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "../App";
import { createMockClient, type ApiClient } from "../api/client";
import { choiceQuery, readChoice } from "../lib/wizard";

function renderAt(url: string, client: ApiClient = createMockClient()) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <App client={client} />
    </MemoryRouter>,
  );
}

describe("WEB-5: wizard bước 1–3", () => {
  it("trang chủ là wizard; chỉ một trường thì chọn sẵn, chọn khung và số kỳ rồi sang bước 4", async () => {
    renderAt("/");
    // Mock chỉ có HUS nên bước 1 đã chọn sẵn và bước 2 hiện ngay.
    const card = await screen.findByRole("radio", { name: /Khoa học máy tính và thông tin/ });
    expect(screen.getByRole("combobox", { name: "Trường" })).toHaveValue("HUS");
    expect(screen.getByRole("button", { name: /Tiếp tục/ })).toBeDisabled();

    await userEvent.click(card);
    expect(screen.getByText(/Khung này có 8 kỳ chuẩn/)).toBeInTheDocument();
    const choices = screen.getAllByRole("radio", { name: /^\d+$/ });
    expect(choices.map((c) => c.getAttribute("value"))).toEqual(
      Array.from({ length: 13 }, (_, i) => String(i)),
    );

    await userEvent.click(screen.getByRole("radio", { name: "3" }));
    await userEvent.click(screen.getByRole("button", { name: /Tiếp tục/ }));
    expect(await screen.findByRole("heading", { name: /Bước 4/ })).toBeInTheDocument();
    expect(screen.getByText(/đã học 3 kỳ/)).toBeInTheDocument();
    expect(screen.getByText("HUS-7480113QTD-2022")).toBeInTheDocument();
  });

  it("đọc lại lựa chọn từ URL và cho chọn 0 kỳ (năm nhất)", async () => {
    renderAt("/?uni=HUS&curriculum=HUS-7460108-2022&ky=0");
    expect(await screen.findByRole("radio", { name: /Khoa học dữ liệu/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: "0" })).toBeChecked();
    expect(screen.getByRole("button", { name: /Tiếp tục/ })).toBeEnabled();
  });

  it("khung không thuộc trường thì báo và không cho tiếp tục", async () => {
    renderAt("/?uni=HUS&curriculum=KHONG-CO&ky=2");
    expect(await screen.findByText(/Không có khung KHONG-CO/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Tiếp tục/ })).toBeDisabled();
  });

  it("lỗi tải danh sách trường hiện thông báo, không phải trang trắng", async () => {
    renderAt("/", createMockClient("error"));
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Tiếp tục/ })).toBeDisabled();
  });

  it("vào /bang-diem khi chưa chọn đủ thì quay về wizard", async () => {
    renderAt("/bang-diem?uni=HUS");
    expect(await screen.findByRole("radio", { name: /Khoa học dữ liệu/ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Bước 4/ })).toBeNull();
  });

  it("luồng nhập mã sinh viên cũ thành link 'Sinh viên mẫu'", async () => {
    renderAt("/");
    await userEvent.click(screen.getByRole("link", { name: "Sinh viên mẫu" }));
    expect(await screen.findByLabelText("Mã sinh viên")).toBeInTheDocument();
  });
});

describe("readChoice / choiceQuery", () => {
  const ky = (v: string) => readChoice(new URLSearchParams({ uni: "HUS", curriculum: "C", ky: v })).semesters;

  it("chỉ nhận số kỳ nguyên trong [0, 12]", () => {
    expect(ky("0")).toBe(0);
    expect(ky("12")).toBe(12);
    for (const bad of ["13", "-1", "2.5", "abc", "", "007"]) expect(ky(bad)).toBeNull();
  });

  it("bỏ mục sau khi mục trước chưa chọn", () => {
    expect(choiceQuery({ uni: "HUS", curriculum: "C", semesters: 0 })).toBe("?uni=HUS&curriculum=C&ky=0");
    expect(choiceQuery({ uni: "HUS", curriculum: "", semesters: 3 })).toBe("?uni=HUS");
    expect(choiceQuery({ uni: "", curriculum: "C", semesters: 3 })).toBe("");
  });
});
