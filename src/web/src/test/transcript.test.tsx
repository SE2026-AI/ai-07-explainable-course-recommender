import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { ApiError, createMockClient, type ApiClient } from "../api/client";
import curriculum from "../api/mocks/contract/curriculum.json";
import type { CurriculumCourse, CurriculumDetail } from "../api/schema";
import type { TranscriptBody } from "../api/transcript";
import namNhat from "../../../../test/fixtures/transcripts/nam-nhat.json";
import { fieldTarget, fromBody, parseScore, prefill, toBody } from "../lib/transcriptDraft";

const UNI = "HUS";
const CODE = "HUS-7480113QTD-2022";

function course(
  course_code: string,
  course_name: string,
  credits: number,
  block_code: string,
  recommended_semester: number | null,
  is_required = true,
): CurriculumCourse {
  return {
    course_code,
    course_name,
    course_name_en: null,
    credits,
    teaching_language: "vi",
    block_code,
    block_name: block_code === "I.2" ? "Ngoại ngữ B1" : "Khối kiến thức chung",
    is_required,
    recommended_semester,
    prerequisite_groups: [],
    primary_topic: null,
    topics: [],
    skills: [],
  } as unknown as CurriculumCourse;
}

/** Danh sách môn dựng cho test: mock hợp đồng §6.3 chỉ có một môn. */
const COURSES = [
  course("PHI1006", "Triết học Mác - Lênin", 3, "I.1", 1),
  course("MAT2400", "Đại số tuyến tính", 4, "I.1", 1),
  course("FLF1107", "Tiếng Anh B1", 5, "I.2", 2, false),
  course("FLF1307", "Tiếng Pháp B1", 5, "I.2", 2, false),
  course("MAT2505", "Lập trình cơ bản", 3, "I.1", 3),
  course("HUS9999", "Môn chưa xếp kỳ", 2, "I.1", null),
];

function client(overrides: Partial<ApiClient> = {}): ApiClient {
  return {
    ...createMockClient(),
    curriculumCourses: async () => ({
      curriculum_code: CODE,
      count: COURSES.length,
      courses: COURSES,
    }),
    curriculum: async () => curriculum as CurriculumDetail,
    ...overrides,
  };
}

function renderAt(semesters: number, c: ApiClient = client()) {
  return render(
    <MemoryRouter initialEntries={[`/bang-diem?uni=${UNI}&curriculum=${CODE}&ky=${semesters}`]}>
      <App client={c} />
    </MemoryRouter>,
  );
}

const row = (code: string) => document.getElementById(`row-${code}`)!;
const pick = (code: string) => within(row(code)).getAllByRole("checkbox")[0];

beforeEach(() => localStorage.clear());
afterEach(() => vi.restoreAllMocks());

describe("WEB-6: nhập bảng điểm", () => {
  it("nhóm môn theo kỳ dự kiến; môn không có kỳ dự kiến xuống cuối", async () => {
    renderAt(2);
    await screen.findByText("Triết học Mác - Lênin");
    const headings = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(headings).toEqual(["Kỳ 1 dự kiến", "Kỳ 2 dự kiến", "Kỳ 3 dự kiến", "Chưa xếp kỳ"]);
  });

  it("điền sẵn kỳ 1..N tick đúng môn, kỳ học = kỳ dự kiến; bỏ tick được từng môn", async () => {
    renderAt(2);
    await userEvent.click(await screen.findByRole("button", { name: "Điền sẵn các môn kỳ 1..2" }));
    for (const code of ["PHI1006", "MAT2400", "FLF1107", "FLF1307"]) expect(pick(code)).toBeChecked();
    expect(pick("MAT2505")).not.toBeChecked();
    expect(pick("HUS9999")).not.toBeChecked();
    expect(screen.getByLabelText("Kỳ học FLF1107")).toHaveValue("2");
    expect(screen.getByLabelText("Kỳ học PHI1006")).toHaveValue("1");

    await userEvent.click(pick("FLF1307"));
    expect(pick("FLF1307")).not.toBeChecked();
    expect(screen.getByText(/Đã tick/).textContent).toBe("Đã tick 3 môn · 12 tín chỉ");
  });

  it("khối tự chọn hiện số tín chỉ đã chọn, không tự quyết đạt hay trượt", async () => {
    renderAt(2);
    const progress = await screen.findByRole("list", { name: "Khối tự chọn" });
    expect(progress).toHaveTextContent("đã chọn 0 / cần 5 tín chỉ");
    await userEvent.click(pick("FLF1107"));
    await userEvent.click(pick("FLF1307"));
    expect(progress).toHaveTextContent("đã chọn 10 / cần 5 tín chỉ");
  });

  it("tìm theo mã hoặc tên và lọc theo khối", async () => {
    renderAt(2);
    await screen.findByText("Triết học Mác - Lênin");
    await userEvent.type(screen.getByPlaceholderText("Tìm theo mã hoặc tên môn"), "mat25");
    expect(screen.getByText("Lập trình cơ bản")).toBeInTheDocument();
    expect(screen.queryByText("Triết học Mác - Lênin")).toBeNull();
    await userEvent.clear(screen.getByPlaceholderText("Tìm theo mã hoặc tên môn"));
    await userEvent.selectOptions(screen.getByLabelText("Lọc theo khối"), "I.2");
    expect(screen.getByText("Tiếng Pháp B1")).toBeInTheDocument();
    expect(screen.queryByText("Lập trình cơ bản")).toBeNull();
  });

  it("môn đã tick mà chưa có điểm thì không gửi, đánh dấu đúng ô", async () => {
    const transcript = vi.fn(createMockClient().transcript);
    renderAt(2, client({ transcript }));
    await userEvent.click(await screen.findByRole("button", { name: "Điền sẵn các môn kỳ 1..2" }));
    await userEvent.type(screen.getByLabelText("Điểm PHI1006"), "7.5");
    await userEvent.click(screen.getByRole("button", { name: "Xem tóm tắt" }));
    expect(transcript).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Điểm MAT2400")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Điểm PHI1006")).not.toHaveAttribute("aria-invalid");
    expect(screen.getByText(/Còn 3 môn đã tick chưa có điểm/)).toBeInTheDocument();
  });

  it("gửi đúng body §6.10 (điểm, Miễn, kỳ học) và hiện tóm tắt từ server", async () => {
    const transcript = vi.fn(createMockClient().transcript);
    renderAt(2, client({ transcript }));
    await screen.findByText("Triết học Mác - Lênin");
    await userEvent.click(pick("MAT2400"));
    await userEvent.type(screen.getByLabelText("Điểm MAT2400"), "3");
    await userEvent.click(pick("PHI1006"));
    await userEvent.click(screen.getByLabelText("Miễn PHI1006"));
    await userEvent.click(pick("FLF1107"));
    await userEvent.type(screen.getByLabelText("Điểm FLF1107"), "8.25");
    await userEvent.selectOptions(screen.getByLabelText("Kỳ học FLF1107"), "1");
    await userEvent.click(screen.getByRole("button", { name: "Xem tóm tắt" }));

    expect(transcript).toHaveBeenCalledOnce();
    const [uni, code, body] = transcript.mock.calls[0];
    expect([uni, code]).toEqual([UNI, CODE]);
    expect(body).toEqual<TranscriptBody>({
      semesters_completed: 2,
      results: [
        { course_code: "PHI1006", semester: 1, exempted: true },
        { course_code: "MAT2400", semester: 1, score: 3 },
        { course_code: "FLF1107", semester: 1, score: 8.25 },
      ],
    });

    // Mock trả nguyên ví dụ §6.10: mọi con số dưới đây là của server.
    const summary = await screen.findByRole("region", {
      name: "Tóm tắt bảng điểm",
    });
    expect(summary).toHaveTextContent("34 / 129");
    expect(summary).toHaveTextContent("2,76");
    expect(summary).toHaveTextContent("Kỳ tới là kỳ 3");
    expect(within(summary).getByText("MAT2505")).toBeInTheDocument();
    expect(summary).toHaveTextContent("Cần học lại Lập trình cơ bản: bạn chưa đạt môn này ở kỳ 2 (điểm 3,0).");
  });

  it("lỗi 422 đánh dấu đúng ô theo details.fields (results[1].score là dòng thứ hai)", async () => {
    const transcript = vi.fn(async () => {
      throw new ApiError(422, "validation_error", "Dữ liệu không hợp lệ.", {
        fields: {
          "results[1].score": "Điểm phải trong [0, 10].",
          "results[0].semester": "Kỳ học phải trong [1, 2].",
        },
      });
    });
    renderAt(2, client({ transcript }));
    await screen.findByText("Triết học Mác - Lênin");
    await userEvent.click(pick("PHI1006"));
    await userEvent.type(screen.getByLabelText("Điểm PHI1006"), "7");
    await userEvent.click(pick("MAT2400"));
    await userEvent.type(screen.getByLabelText("Điểm MAT2400"), "11");
    await userEvent.click(screen.getByRole("button", { name: "Xem tóm tắt" }));

    expect(await screen.findByText("Điểm phải trong [0, 10].")).toBeInTheDocument();
    expect(screen.getByLabelText("Điểm MAT2400")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Kỳ học PHI1006")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Điểm PHI1006")).not.toHaveAttribute("aria-invalid");
    expect(within(row("MAT2400")).getByRole("alert")).toHaveTextContent("Điểm phải trong [0, 10].");
  });

  it("chưa học kỳ nào: không có danh sách môn, gửi results rỗng", async () => {
    const transcript = vi.fn(createMockClient().transcript);
    renderAt(0, client({ transcript }));
    expect(await screen.findByText(/chưa học xong kỳ nào/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Xem tóm tắt" }));
    expect(transcript.mock.calls[0][2]).toEqual({
      semesters_completed: 0,
      results: [],
    });
  });

  it("bảng điểm còn nguyên khi quay lại trang", async () => {
    const first = renderAt(2);
    await screen.findByText("Triết học Mác - Lênin");
    await userEvent.click(pick("MAT2400"));
    await userEvent.type(screen.getByLabelText("Điểm MAT2400"), "6.5");
    first.unmount();
    renderAt(2);
    await screen.findByText("Triết học Mác - Lênin");
    expect(pick("MAT2400")).toBeChecked();
    expect(screen.getByLabelText("Điểm MAT2400")).toHaveValue(6.5);
  });
});

describe("WEB-8: xuất và nhập file JSON", () => {
  const file = (data: unknown) =>
    new File([JSON.stringify(data)], "bang-diem.json", {
      type: "application/json",
    });

  it("nhập file mẫu của test/fixtures/transcripts: tick đúng môn và chuyển sang số kỳ trong file", async () => {
    const user = userEvent.setup();
    renderAt(2);
    await screen.findByText("Triết học Mác - Lênin");
    await user.upload(screen.getByLabelText("Nhập file JSON"), file(namNhat));
    expect(await screen.findByRole("button", { name: "Điền sẵn các môn kỳ 1..1" })).toBeInTheDocument();
    expect(screen.getByText(/Đã tick/)).toHaveTextContent(`Đã tick ${namNhat.request.results.length} môn`);
  });

  it("từ chối file của khung khác hoặc sai dạng, giữ nguyên bản nháp", async () => {
    const user = userEvent.setup();
    renderAt(2);
    await screen.findByText("Triết học Mác - Lênin");
    await user.upload(
      screen.getByLabelText("Nhập file JSON"),
      file({ ...namNhat, curriculum_code: "HUS-7460108-2022" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("khung HUS-7460108-2022");
    await user.upload(screen.getByLabelText("Nhập file JSON"), file({ semesters_completed: 40, results: [] }));
    expect(await screen.findByRole("alert")).toHaveTextContent("semesters_completed");
    expect(screen.getByText(/Đã tick/)).toHaveTextContent("Đã tick 0 môn");
  });

  it("xuất file là body §6.10 theo thứ tự khung", async () => {
    const user = userEvent.setup();
    let blob: Blob | undefined;
    URL.createObjectURL = vi.fn((b: Blob) => {
      blob = b;
      return "blob:x";
    });
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    renderAt(1);
    await screen.findByText("Triết học Mác - Lênin");
    await user.click(pick("MAT2400"));
    await user.click(screen.getByLabelText("Miễn MAT2400"));
    await user.click(screen.getByRole("button", { name: "Xuất file JSON" }));
    expect(click).toHaveBeenCalled();
    const text = await new Promise<string>((ok) => {
      const reader = new FileReader();
      reader.onload = () => ok(String(reader.result));
      reader.readAsText(blob!);
    });
    expect(JSON.parse(text)).toEqual({
      semesters_completed: 1,
      results: [{ course_code: "MAT2400", semester: 1, exempted: true }],
    });
  });
});

describe("transcriptDraft", () => {
  it("parseScore nhận dấu phẩy và dấu chấm, từ chối chuỗi rỗng", () => {
    expect(parseScore("7,5")).toBe(7.5);
    expect(parseScore(" 10 ")).toBe(10);
    for (const bad of ["", "-1", "abc", "7,"]) expect(parseScore(bad)).toBeNull();
  });

  it("toBody giữ thứ tự danh sách môn; fieldTarget đổi đường dẫn lỗi về đúng môn", () => {
    const draft = prefill({}, COURSES, 1);
    draft.PHI1006.score = "5";
    draft.MAT2400.exempted = true;
    const { body, codes } = toBody(draft, COURSES, 1);
    expect(codes).toEqual(["PHI1006", "MAT2400"]);
    expect(body.results[1]).toEqual({
      course_code: "MAT2400",
      semester: 1,
      exempted: true,
    });
    expect(fieldTarget("results[1].score", codes)).toEqual({
      course: "MAT2400",
      field: "score",
    });
    expect(fieldTarget("results[0]", codes)).toEqual({
      course: "PHI1006",
      field: "course_code",
    });
    expect(fieldTarget("results[5].score", codes)).toBeNull();
    expect(fieldTarget("semesters_completed", codes)).toBeNull();
  });

  it.each(
    Object.entries(
      import.meta.glob("../../../../test/fixtures/transcripts/*.json", {
        eager: true,
        import: "default",
      }),
    ),
  )("fromBody đọc được bảng điểm mẫu %s", (_name, data) => {
    const { request } = data as {
      request: { semesters_completed: number; results: unknown[] };
    };
    const parsed = fromBody(request)!;
    expect(parsed.semesters).toBe(request.semesters_completed);
    expect(Object.keys(parsed.draft)).toHaveLength(request.results.length);
  });

  it("fromBody đọc được bảng điểm mẫu trong test/fixtures/transcripts", () => {
    const parsed = fromBody(namNhat.request)!;
    expect(parsed.semesters).toBe(1);
    expect(parsed.draft.MAT2501).toEqual({
      semester: 1,
      score: "6.3",
      exempted: false,
    });
  });
});
