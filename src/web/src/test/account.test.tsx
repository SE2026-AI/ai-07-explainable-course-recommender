import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { createMockClient, type ApiClient } from "../api/client";
import { ApiError } from "../api/errors";
import curriculum from "../api/mocks/contract/curriculum.json";
import { createMockAccountClient } from "../api/v2/mock";
import { createLiveAccountClient } from "../api/v2/client";
import type { AccountClient } from "../api/v2/types";
import type { CurriculumDetail } from "../api/schema";

const CODE = "HUS-7480113QTD-2022";
const credentials = { email: "student@example.test", password: "fake-password-only" };
const body = { semesters_completed: 1, results: [{ course_code: "MAT2400", semester: 1, score: 7.5 }] };
const client: ApiClient = {
  ...createMockClient(),
  curriculum: async () => curriculum as CurriculumDetail,
  curriculumCourses: async () => ({ curriculum_code: CODE, count: 1, courses: [{
    course_code: "MAT2400", course_name: "Đại số tuyến tính", credits: 4, block_code: "I.1", block_name: "Khối chung",
    is_required: true, recommended_semester: 1, prerequisite_groups: [], teaching_language: "vi", topics: [], skills: [],
  }] }),
};
function Path() { return <output data-testid="location">{useLocation().pathname}{useLocation().search}</output>; }
function at(path: string, api = createMockAccountClient()) {
  return render(<MemoryRouter initialEntries={[path]}><App client={client} accountClient={api} /><Path /></MemoryRouter>);
}
async function prepared(): Promise<AccountClient> {
  const api = createMockAccountClient(); await api.register(credentials); await api.profile({ curriculum_code: CODE }); return api;
}
beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe("WEB-9 account flow", () => {
  it("expiry while reading a protected page redirects with the full return path", async () => {
    const session = { user: { user_id: "mock-id", email: credentials.email, role: "student", created_at: "2026-11-28T00:00:00Z" },
      profile: { university_code: "HUS", curriculum_code: CODE, semesters_completed: 1, updated_at: "2026-11-28T00:00:00Z" } };
    vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(url.endsWith("/me") ? session :
      { error: { code: "unauthenticated", message: "Expired", details: {} } }), { status: url.endsWith("/me") ? 200 : 401 })));
    at("/cua-toi?source=resume", createLiveAccountClient());
    await screen.findByLabelText("Email");
    expect(screen.getByTestId("location")).toHaveTextContent("/dang-nhap?next=%2Fcua-toi%3Fsource%3Dresume");
  });
  it("registers,chooses HUS curriculum and opens reused transcript editor", async () => {
    const api = createMockAccountClient(); at("/dang-ky", api);
    await userEvent.type(await screen.findByLabelText("Email"), credentials.email);
    await userEvent.type(screen.getByLabelText("Mật khẩu"), credentials.password);
    await userEvent.click(screen.getByRole("button", { name: "Đăng ký" }));
    await screen.findByRole("heading", { name: "Khung chương trình của tôi" });
    await screen.findByRole("option", { name: new RegExp(CODE) });
    await userEvent.selectOptions(screen.getByLabelText("Chương trình đào tạo"), CODE);
    await userEvent.click(screen.getByRole("button", { name: "Lưu khung chương trình" }));
    await screen.findByText("Đã lưu khung chương trình.");
    await userEvent.click(screen.getAllByRole("link", { name: "Bảng điểm của tôi" })[0]);
    await screen.findByRole("button", { name: "Lưu bảng điểm" });
    expect((await api.me()).profile?.university_code).toBe("HUS");
  });
  it("401 on protected route returns to the same internal path after login", async () => {
    const api = await prepared(); await api.logout(); at("/cua-toi/tien-trinh?view=blocks", api);
    await userEvent.type(await screen.findByLabelText("Email"), credentials.email);
    expect(screen.getByTestId("location")).toHaveTextContent("/dang-nhap?next=");
    await userEvent.type(screen.getByLabelText("Mật khẩu"), credentials.password);
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
    await screen.findByRole("heading", { name: "Tiến trình học tập của tôi" });
    expect(screen.getByTestId("location")).toHaveTextContent("/cua-toi/tien-trinh?view=blocks");
  });
  it("does not delete without an explicit password form submit", async () => {
    const api = await prepared(); const remove = vi.spyOn(api, "deleteAccount"); at("/tai-khoan", api);
    await userEvent.click(await screen.findByRole("button", { name: "Tôi muốn xóa tài khoản" }));
    expect(remove).not.toHaveBeenCalled();
    const form = screen.getByRole("form", { name: "Xác nhận xóa tài khoản" });
    await userEvent.type(within(form).getByLabelText("Nhập mật khẩu để xác nhận xóa"), credentials.password);
    await userEvent.click(within(form).getByRole("button", { name: "Xóa vĩnh viễn tài khoản" }));
    await screen.findByLabelText("Email"); expect(remove).toHaveBeenCalledWith({ password: credentials.password });
  });
  it("changes password without copying it to localStorage", async () => {
    const api = await prepared(); const change = vi.spyOn(api, "password"); at("/tai-khoan", api);
    await userEvent.type(await screen.findByLabelText("Mật khẩu hiện tại"), credentials.password);
    await userEvent.type(screen.getByLabelText("Mật khẩu mới"), "new-fake-password-only");
    await userEvent.click(screen.getByRole("button", { name: "Đổi mật khẩu" }));
    await screen.findByText("Đã đổi mật khẩu. Các phiên khác đã được đăng xuất.");
    expect(change).toHaveBeenCalledOnce(); expect(localStorage.length).toBe(0);
    expect(screen.getByLabelText("Mật khẩu mới")).toHaveValue("");
  });
});

describe("WEB-10 saved transcript", () => {
  it("JSON import changes semesters in the account editor without navigating to the public wizard", async () => {
    const api = await prepared(); const save = vi.spyOn(api, "saveTranscript"); at("/cua-toi", api);
    const input = await screen.findByLabelText("Nhập file JSON");
    await userEvent.upload(input, new File([JSON.stringify(body)], "mock-transcript.json", { type: "application/json" }));
    await waitFor(() => expect(screen.getByLabelText("Số kỳ đã hoàn thành trên tài khoản")).toHaveValue(1));
    expect(screen.getByTestId("location")).toHaveTextContent("/cua-toi");
    expect(save).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Lưu bảng điểm" }));
    await waitFor(() => expect(save).toHaveBeenCalledWith(body));
    expect(localStorage.length).toBe(0);
  });
  it("only uploads an existing local draft after consent;clears only that draft after successful save", async () => {
    const api = await prepared(); const save = vi.spyOn(api, "saveTranscript");
    localStorage.setItem(`ai07.transcript.HUS.${CODE}`, JSON.stringify(body)); localStorage.setItem("unrelated", "keep");
    at("/cua-toi", api);
    const prompt = await screen.findByRole("region", { name: "Bản nháp trên trình duyệt" });
    expect(save).not.toHaveBeenCalled();
    await userEvent.click(within(prompt).getByRole("button", { name: "Đưa bản nháp lên tài khoản" }));
    await waitFor(() => expect(save).toHaveBeenCalledOnce());
    await waitFor(() => expect(localStorage.getItem(`ai07.transcript.HUS.${CODE}`)).toBeNull());
    expect(localStorage.getItem("unrelated")).toBe("keep"); expect((await api.transcript()).results).toEqual(body.results);
  });
  it("declining migration leaves local draft untouched and account empty", async () => {
    const api = await prepared(); const save = vi.spyOn(api, "saveTranscript");
    localStorage.setItem(`ai07.transcript.HUS.${CODE}`, JSON.stringify(body)); at("/cua-toi", api);
    await userEvent.click(await screen.findByRole("button", { name: "Không đưa lên tài khoản" }));
    expect(save).not.toHaveBeenCalled(); expect((await api.transcript()).results).toEqual([]);
    expect(localStorage.getItem(`ai07.transcript.HUS.${CODE}`)).not.toBeNull();
  });
  it("saving maps422 to correct course cell and never writes the account transcript to localStorage", async () => {
    const api = await prepared(); await api.saveTranscript(body);
    const save = vi.spyOn(api, "saveTranscript").mockRejectedValue(new ApiError(422, "validation_error", "invalid", { fields: { "results[0].score": "Điểm chưa hợp lệ ở môn này." } }));
    at("/cua-toi", api);
    await userEvent.click(await screen.findByRole("button", { name: "Lưu bảng điểm" }));
    const row = document.getElementById("row-MAT2400")!;
    await waitFor(() => expect(row).toHaveClass("invalid"));
    expect(row).toHaveTextContent("Điểm chưa hợp lệ ở môn này."); expect(save).toHaveBeenCalledOnce();
    expect(localStorage.length).toBe(0);
  });
  it("curriculum409 offers explicit clear-first path,without silently deleting on initial submit", async () => {
    const api = await prepared(); await api.saveTranscript(body); const save = vi.spyOn(api, "saveTranscript"); at("/tai-khoan", api);
    await screen.findByRole("option", { name: /HUS-7460108-2022/ });
    await userEvent.selectOptions(await screen.findByLabelText("Chương trình đào tạo"), "HUS-7460108-2022");
    await userEvent.click(screen.getByRole("button", { name: "Lưu khung chương trình" }));
    await screen.findByRole("alertdialog", { name: "Đổi khung và xóa bảng điểm" }); expect(save).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Xóa bảng điểm và đổi khung" }));
    await screen.findByText("Đã xóa bảng điểm và đổi khung.");
    expect((await api.me()).profile?.curriculum_code).toBe("HUS-7460108-2022");
  });
  it("progress renders GPA,blocks and supplementary-skills condition separately", async () => {
    const api = await prepared(); at("/cua-toi/tien-trinh", api);
    await screen.findByRole("heading", { name: "Tiến trình học tập của tôi" });
    expect(screen.getByRole("progressbar", { name: "Tín chỉ tốt nghiệp đã hoàn thành" })).toHaveAttribute("aria-valuemax", "129");
    expect(screen.getByRole("heading", { name: "Điều kiện tốt nghiệp ngoài tổng tín chỉ" })).toBeInTheDocument();
    expect(screen.getByText(/Còn thiếu: HUS1012/)).toBeInTheDocument();
  });
});
