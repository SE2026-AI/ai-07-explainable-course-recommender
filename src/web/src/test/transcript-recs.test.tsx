import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { ApiError, createMockClient, type ApiClient } from "../api/client";
import type { CurriculumCourse } from "../api/schema";

const UNI = "HUS";
const CODE = "HUS-7480113QTD-2022";
const COURSES = [
  {
    course_code: "PHI1006",
    course_name: "Triết học",
    credits: 3,
    block_code: "I.1",
    recommended_semester: 1,
  },
  {
    course_code: "MAT2505",
    course_name: "Lập trình cơ bản",
    credits: 3,
    block_code: "III",
    recommended_semester: 2,
  },
] as unknown as CurriculumCourse[];
const DRAFT = {
  semesters_completed: 2,
  results: [
    { course_code: "MAT2505", semester: 2, score: 3 },
    { course_code: "PHI1006", semester: 1, exempted: true },
  ],
};

function setup(overrides: Partial<ApiClient> = {}) {
  const base = createMockClient();
  const client: ApiClient = {
    ...base,
    curriculumCourses: async () => ({
      curriculum_code: CODE,
      count: COURSES.length,
      courses: COURSES,
    }),
    ...overrides,
  };
  const spy = vi.spyOn(client, "recommendTranscript");
  render(
    <MemoryRouter
      initialEntries={[`/goi-y?uni=${UNI}&curriculum=${CODE}&ky=2`]}
    >
      <App client={client} />
    </MemoryRouter>,
  );
  return spy;
}

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(`ai07.transcript.${UNI}.${CODE}`, JSON.stringify(DRAFT));
});

describe("WEB-7: gợi ý cho bảng điểm tự nhập (§6.11)", () => {
  it("gửi bảng điểm của bước 4 theo thứ tự khung, hiện khoảng tín chỉ, gợi ý và lý do chưa xếp từ server", async () => {
    const spy = setup();
    expect(await screen.findByTestId("credit-window")).toHaveTextContent(
      "Tổng 20 tín chỉ, trong khoảng 15–20 bạn đặt.",
    );
    expect(spy.mock.calls[0][2]).toEqual({
      semesters_completed: 2,
      results: [
        { course_code: "PHI1006", semester: 1, exempted: true },
        { course_code: "MAT2505", semester: 2, score: 3 },
      ],
      skip: [],
      include: [],
    });
    expect(screen.getByText("Khối tự chọn đã đủ tín chỉ")).toBeInTheDocument();
    expect(screen.getByText("Vượt số tín chỉ tối đa")).toBeInTheDocument();
    expect(
      screen.getByText(/cần hoàn thành Xác suất - Thống kê/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Quay lại sửa bảng điểm" }),
    ).toHaveAttribute(
      "href",
      `/bang-diem?uni=${UNI}&curriculum=${encodeURIComponent(CODE)}&ky=2`,
    );
    expect(screen.queryByText(/kịch bản giả định/)).not.toBeInTheDocument();
  });

  it("chưa học / học kỳ này gửi skip và include, một mã chỉ ở một danh sách", async () => {
    const user = userEvent.setup();
    const spy = setup();
    await screen.findByTestId("credit-window");
    await user.click(
      screen.getAllByRole("button", { name: "Chưa học kỳ này" })[0],
    );
    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        UNI,
        CODE,
        expect.objectContaining({ skip: ["MAT2505"], include: [] }),
        expect.anything(),
      ),
    );
    expect(await screen.findByText(/kịch bản giả định/)).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "Học kỳ này" })[0]);
    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        UNI,
        CODE,
        expect.objectContaining({ skip: ["MAT2505"], include: ["HUS1024"] }),
        expect.anything(),
      ),
    );
    // Mock phát lại nguyên ví dụ nên bỏ chọn qua chip ở khung Điều chỉnh.
    await user.click(screen.getByRole("button", { name: "Bỏ MAT2505" }));
    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        UNI,
        CODE,
        expect.objectContaining({ skip: [], include: ["HUS1024"] }),
        expect.anything(),
      ),
    );
  });

  it("Áp dụng gửi khoảng tín chỉ; trọng số interest không có thanh chỉnh", async () => {
    const user = userEvent.setup();
    const spy = setup();
    await screen.findByTestId("credit-window");
    expect(screen.queryByText("Chủ đề bạn quan tâm")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Tín chỉ tối thiểu (từ 10)"), "15");
    await user.type(screen.getByLabelText("Tín chỉ tối đa"), "18");
    await user.click(screen.getByRole("button", { name: "Áp dụng" }));
    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        UNI,
        CODE,
        expect.objectContaining({ min_credits: 15, max_credits: 18 }),
        expect.anything(),
      ),
    );
  });

  it("422 ở results[i] chỉ ra môn trong bảng điểm và dẫn về bước 4", async () => {
    setup({
      recommendTranscript: async () => {
        throw new ApiError(
          422,
          "validation_error",
          "Dữ liệu gửi lên không hợp lệ.",
          {
            fields: { "results[1].score": "Điểm vượt thang của khung." },
          },
        );
      },
    });
    expect(
      await screen.findByText("bảng điểm, môn MAT2505"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Sửa bảng điểm" }),
    ).toBeInTheDocument();
  });
});
