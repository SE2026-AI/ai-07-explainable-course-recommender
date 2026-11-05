import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "../App";
import { ApiError, createMockClient, type ApiClient } from "../api/client";
import courseStatus from "../api/mocks/contract/course-status.json";
import profile from "../api/mocks/contract/profile.json";
import recommendations from "../api/mocks/contract/recommendations.json";
import planCheck from "../api/mocks/contract/plan-check.json";
import type { CourseStatus, PlanCheck, PrerequisiteGraph, Recommendations, StudentProfile } from "../api/schema";
import { layout } from "../components/PrereqGraph";

const base = "/students/HUS/T03";

function client(overrides: Partial<ApiClient> = {}): ApiClient {
  return { ...createMockClient(), ...overrides };
}

function renderAt(url: string, c: ApiClient = client()) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <App client={c} />
    </MemoryRouter>,
  );
}

describe("WEB-2: chọn sinh viên", () => {
  it("chọn trường, nhập mã sinh viên rồi mở hồ sơ; không có đăng nhập", async () => {
    renderAt("/students");
    expect(screen.queryByLabelText(/mật khẩu/i)).toBeNull();
    await screen.findByRole("option", { name: /HUS/ });
    await userEvent.type(screen.getByLabelText("Mã sinh viên"), "T03");
    await userEvent.click(screen.getByRole("button", { name: "Xem" }));
    expect(await screen.findByText("Tiến độ học tập")).toBeInTheDocument();
  });

  it("404 student_not_found hiện thông báo rõ, không phải trang trắng", async () => {
    renderAt(`${base}/profile`, createMockClient("error"));
    const alerts = await screen.findAllByRole("alert");
    const alert = alerts.find((a) => a.textContent?.includes("student_not_found"))!;
    expect(alert).toHaveTextContent("Không tìm thấy sinh viên");
    expect(alert).toHaveTextContent("student_not_found");
    expect(screen.getByRole("link", { name: "Nhập mã sinh viên khác" })).toBeInTheDocument();
  });
});

describe("WEB-2: hồ sơ (§6.4)", () => {
  it("hiện tín chỉ, GPA, môn đang nợ, kỳ trong lộ trình và tiến độ từng khối có tên khối", async () => {
    renderAt(`${base}/profile`);
    expect(await screen.findByText("34 / 129")).toBeInTheDocument();
    expect(screen.getByText("2,76")).toBeInTheDocument();
    expect(screen.getByText(/Kỳ 3/)).toBeInTheDocument();
    expect(screen.getByText("MAT2505")).toBeInTheDocument();
    const row = (await screen.findByText("Ngoại ngữ B1")).closest("tr")!;
    expect(within(row).getByText("5 / 5")).toBeInTheDocument();
  });

  it("gpa null hiện 'Chưa có điểm', không hiện 0", async () => {
    const p = { ...(profile as StudentProfile), gpa: null };
    renderAt(`${base}/profile`, client({ profile: async () => p }));
    expect(await screen.findByText("Chưa có điểm")).toBeInTheDocument();
    expect(screen.queryByText(/^0$/)).toBeNull();
  });

  it("không hiện fairness_group/gender kể cả khi phản hồi lỡ chứa (§6.4, §9.5)", async () => {
    const p = { ...(profile as StudentProfile), fairness_group: "G1", gender: "nữ" } as StudentProfile;
    const { container } = renderAt(`${base}/profile`, client({ profile: async () => p }));
    await screen.findByText("Tiến độ học tập");
    expect(container.textContent).not.toMatch(/G1|nữ|fairness|gender/);
  });
});

describe("WEB-2: trạng thái học phần (§6.5)", () => {
  it("nhóm theo trạng thái, đếm theo summary và hiện câu của server", async () => {
    renderAt(`${base}/status`);
    expect(await screen.findByText(/Cần học lại Lập trình cơ bản/)).toBeInTheDocument();
    // summary của ví dụ: missing_prerequisite 33 dù chỉ có 1 dòng trong ví dụ rút gọn
    expect(screen.getByText("33")).toBeInTheDocument();
    expect(screen.getByText(/Chưa học được Học máy/)).toBeInTheDocument();
    const attempts = screen.getAllByText(/Lần học gần nhất: học kỳ/).map((e) => e.textContent);
    expect(attempts).toContain("Lần học gần nhất: học kỳ 20252, lần 1 · điểm 3 (F)");
  });

  it("missing_prerequisites hiện đúng VÀ/HOẶC", async () => {
    const s = structuredClone(courseStatus) as CourseStatus;
    s.courses[1].missing_prerequisites = [["MAT2323", "MAT2406"], ["MAT2505"]];
    renderAt(`${base}/status`, client({ courseStatus: async () => s }));
    const row = (await screen.findByText("Học máy")).closest("li")!;
    expect(within(row).getByText(/Còn thiếu/)).toHaveTextContent("Còn thiếu: (MAT2323 hoặc MAT2406) và MAT2505");
  });

  it("kịch bản rỗng có thông báo", async () => {
    renderAt(`${base}/status`, client({ courseStatus: createMockClient("empty").courseStatus }));
    expect(await screen.findByText("Khung chương trình chưa có học phần nào.")).toBeInTheDocument();
  });
});

describe("WEB-3: gợi ý (§6.6)", () => {
  it("render đúng ví dụ §6.6, giữ thứ tự server, hiện tổng đóng góp cạnh score", async () => {
    renderAt(`${base}/recommendations`);
    await screen.findByText("Lập trình cơ bản");
    const recs = document.querySelectorAll(".rec");
    expect([...recs].map((r) => r.querySelector(".rec-title .mono")?.textContent)).toEqual(["MAT2505", "MAT2323"]);
    expect(recs[0]).toHaveTextContent("5,7083");
    expect(recs[0]).toHaveTextContent("= tổng đóng góp 5,7083");
    // lý do động: 4 lý do ở môn 1, 3 lý do ở môn 2, không có ô cố định 6 tiêu chí
    expect(recs[0].querySelectorAll(".reasons > li")).toHaveLength(4);
    expect(recs[1].querySelectorAll(".reasons > li")).toHaveLength(3);
    expect(within(recs[0] as HTMLElement).getByText("MAT3560")).toBeInTheDocument();
    // vì sao chưa: từ not_eligible của cùng phản hồi
    expect(screen.getByText(/Chưa học được Học máy/)).toBeInTheDocument();
  });

  it("score lệch tổng đóng góp thì cảnh báo", async () => {
    const r = structuredClone(recommendations) as Recommendations;
    r.items![0].score = 9;
    renderAt(`${base}/recommendations`, client({ recommendations: async () => r }));
    expect(await screen.findByText(/khác điểm 9/)).toBeInTheDocument();
  });

  it("môn không có lý do nào không làm vỡ UI", async () => {
    const r = structuredClone(recommendations) as Recommendations;
    r.items![1].reasons = [];
    r.items![1].score = 0;
    renderAt(`${base}/recommendations`, client({ recommendations: async () => r }));
    expect(await screen.findByText("Không có lý do nào góp điểm cho môn này.")).toBeInTheDocument();
  });

  it("đổi trọng số và giả định thì gửi POST; what_if hiện cảnh báo kịch bản giả định", async () => {
    const bodies: unknown[] = [];
    const mock = createMockClient();
    renderAt(
      `${base}/recommendations`,
      client({
        recommend: (ref, body, s) => {
          bodies.push(body);
          return mock.recommend(ref, body, s);
        },
      }),
    );
    await screen.findByText("Lập trình cơ bản");
    await userEvent.click(screen.getByRole("button", { name: "+ Thêm giả định" }));
    await userEvent.selectOptions(screen.getByLabelText("Môn giả định"), "MAT2505");
    await userEvent.type(screen.getByLabelText("Điểm giả định"), "6");
    await userEvent.click(screen.getByRole("button", { name: "Áp dụng" }));
    expect(await screen.findByText("kịch bản giả định")).toBeInTheDocument();
    expect(bodies[0]).toMatchObject({
      limit: 5,
      assumptions: [{ course_code: "MAT2505", status: "passed", score: 6 }],
      skip: [],
      swap: [],
    });
    expect(bodies[0]).not.toHaveProperty("weights");
  });

  it("422 hiện được trường nào sai từ details.fields", async () => {
    const err = new ApiError(422, "validation_error", "Dữ liệu gửi lên không hợp lệ.", {
      fields: { limit: "Input should be less than or equal to 20" },
    });
    renderAt(`${base}/recommendations`, client({ recommend: async () => Promise.reject(err) }));
    await screen.findByText("Lập trình cơ bản");
    await userEvent.clear(screen.getByLabelText("Số gợi ý (tối đa 20)"));
    await userEvent.type(screen.getByLabelText("Số gợi ý (tối đa 20)"), "25");
    await userEvent.click(screen.getByRole("button", { name: "Áp dụng" }));
    const fields = await screen.findByLabelText("Trường bị lỗi");
    expect(fields).toHaveTextContent("limit: Input should be less than or equal to 20");
  });
});

describe("WEB-4: kế hoạch học kỳ (§6.7)", () => {
  it("kế hoạch rỗng cho valid = true", async () => {
    renderAt(`${base}/plan`, client({ planCheck: createMockClient("empty").planCheck }));
    expect(await screen.findByText("Hợp lệ")).toBeInTheDocument();
    expect(screen.getByText("Kế hoạch đang trống.")).toBeInTheDocument();
    expect(screen.getByText(/không được\s+tính là đã đạt/)).toBeInTheDocument();
  });

  it("vi phạm cả 6 mã hiện đủ 6 dòng, kể cả nhiều vi phạm trên một môn", async () => {
    const codes = [
      "credit_limit_exceeded",
      "missing_prerequisite",
      "already_passed",
      "block_limit_exceeded",
      "duplicate_course",
      "not_in_curriculum",
    ];
    const res: PlanCheck = {
      ...(planCheck as PlanCheck),
      valid: false,
      violations: codes.map((code, i) => ({
        code,
        course_code: i === 0 ? null : "MAT3533",
        text: `câu ${code}`,
        data: {},
      })),
    };
    localStorage.setItem("ai07.plan.HUS.T03", JSON.stringify(["MAT3533"]));
    renderAt(`${base}/plan`, client({ planCheck: async () => res }));
    expect(await screen.findByText("Chưa hợp lệ")).toBeInTheDocument();
    for (const code of codes) expect(screen.getByText(`câu ${code}`)).toBeInTheDocument();
    expect(document.querySelectorAll(".violations > li")).toHaveLength(6);
    localStorage.clear();
  });
});

describe("WEB-4: sơ đồ tiên quyết (§6.9)", () => {
  it("dựng sơ đồ từ ví dụ hợp đồng; hai nhóm khác group_no là hai cạnh VÀ", async () => {
    renderAt(`${base}/graph`);
    await screen.findByRole("img", { name: "Sơ đồ tiên quyết" });
    expect(document.querySelectorAll("[data-node]")).toHaveLength(5);
    expect(document.querySelector('[data-edge="MAT3507>MAT3534"]')).toHaveClass("and");
    expect(document.querySelector('[data-edge="MAT2323>MAT3534"]')).toHaveClass("and");
    expect(document.querySelectorAll("[data-or-group]")).toHaveLength(0);
    // tô màu theo course-status của sinh viên: MAT2323 eligible, MAT3533 missing_prerequisite
    expect(document.querySelector('[data-node="MAT2323"]')).toHaveClass("status-eligible");
    expect(document.querySelector('[data-node="MAT3533"]')).toHaveClass("status-missing_prerequisite");
  });

  it("cùng group_no thì vẽ thành một nhóm HOẶC, không làm phẳng", async () => {
    const graph: PrerequisiteGraph = {
      curriculum_code: "X",
      nodes: [
        { course_code: "A", course_name: "A", credits: 3, block_code: "I", recommended_semester: 1 },
        { course_code: "B", course_name: "B", credits: 3, block_code: "I", recommended_semester: 1 },
        { course_code: "C", course_name: "C", credits: 3, block_code: "I", recommended_semester: 1 },
        { course_code: "T", course_name: "T", credits: 3, block_code: "I", recommended_semester: 2 },
      ],
      edges: [
        { course_code: "T", group_no: 1, required_course_code: "A" },
        { course_code: "T", group_no: 1, required_course_code: "B" },
        { course_code: "T", group_no: 2, required_course_code: "C" },
      ],
    };
    expect(layout(graph.nodes!, graph.edges!).groups.get("T")).toEqual([["A", "B"], ["C"]]);
    renderAt(`${base}/graph`, client({ prerequisiteGraph: async () => graph }));
    await screen.findByRole("img", { name: "Sơ đồ tiên quyết" });
    expect(document.querySelector('[data-or-group="T:A|B"]')).not.toBeNull();
    expect(document.querySelector('[data-edge="A>T"]')).toHaveClass("or");
    expect(document.querySelector('[data-edge="C>T"]')).toHaveClass("and");
  });
});
