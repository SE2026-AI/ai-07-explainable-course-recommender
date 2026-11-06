// Mock phát lại nguyên văn ví dụ JSON của docs/architecture/api-contract.md (§5, §6.1–6.9).
// Hợp đồng không có ví dụ cho health, universities, terms, curricula; bốn file trong mocks/seed/
// là phản hồi thật của backend trên data/seed. Không tự nghĩ ra dữ liệu ở đây, và không tính
// trạng thái, điểm hay thứ hạng: mock không biết mã sinh viên, học kỳ hay trọng số được gửi.
import meta from "./mocks/contract/meta.json";
import curriculum from "./mocks/contract/curriculum.json";
import curriculumCourses from "./mocks/contract/curriculum-courses.json";
import dataIssues from "./mocks/contract/data-issues.json";
import profile from "./mocks/contract/profile.json";
import courseStatus from "./mocks/contract/course-status.json";
import recommendations from "./mocks/contract/recommendations.json";
import planCheck from "./mocks/contract/plan-check.json";
import graph from "./mocks/contract/prerequisite-graph.json";
import studentNotFound from "./mocks/contract/error-student-not-found.json";
import health from "./mocks/seed/health.json";
import universities from "./mocks/seed/universities.json";
import terms from "./mocks/seed/terms.json";
import curricula from "./mocks/seed/curricula.json";
import { ApiError } from "./errors";
import type { ApiClient } from "./client";
import type {
  CourseStatus,
  CurriculumCourses,
  CurriculumDetail,
  CurriculumSummary,
  DataIssues,
  Meta,
  PlanCheck,
  PrerequisiteGraph,
  RecommendationBody,
  Recommendations,
  StudentProfile,
  Term,
  University,
} from "./schema";

/** success: ví dụ hợp đồng; empty: danh sách rỗng; error: mỗi endpoint trả lỗi §5. */
export type MockScenario = "success" | "empty" | "error";

const internal = () =>
  new ApiError(500, "internal_error", "Đã xảy ra lỗi nội bộ. Vui lòng thử lại sau.", {});
const noUniversity = (uni: string) =>
  new ApiError(404, "university_not_found", `Không tìm thấy trường đại học '${uni}'.`, {
    university_code: uni,
  });
const noCurriculum = (uni: string, code: string) =>
  new ApiError(404, "curriculum_not_found", `Không tìm thấy khung chương trình '${code}'.`, {
    university_code: uni,
    curriculum_code: code,
  });
/** Ví dụ lỗi của §5, nguyên văn. */
const noStudent = () => ApiError.fromBody(404, studentNotFound);

const emptyStatus: CourseStatus = {
  ...(courseStatus as CourseStatus),
  summary: { passed: 0, retake: 0, eligible: 0, missing_prerequisite: 0, block_complete: 0 },
  courses: [],
};
const emptyRecommendations: Recommendations = {
  ...(recommendations as Recommendations),
  candidate_count: 0,
  items: [],
  not_eligible: [],
};

/** §6.6 quy định 6: `what_if` theo request. Đây là phần duy nhất mock phản chiếu từ request. */
function whatIf(body: RecommendationBody): boolean {
  return Boolean(body.assumptions?.length || body.skip?.length || body.swap?.length);
}

export function mockClient(scenario: MockScenario): ApiClient {
  async function replay<T>(data: T, empty: T, error: () => ApiError, signal?: AbortSignal) {
    signal?.throwIfAborted();
    if (scenario === "error") throw error();
    return structuredClone(scenario === "empty" ? empty : data);
  }
  const emptyCourses = (code: string): CurriculumCourses => ({ curriculum_code: code, count: 0, courses: [] });

  return {
    mode: "mock",
    health: (s) => replay(health, health, internal, s),
    meta: (s) => replay(meta as Meta, { ...(meta as Meta), curriculum_codes: [] }, internal, s),
    universities: (s) => replay(universities as University[], [], internal, s),
    terms: (uni, s) => replay(terms as Term[], [], () => noUniversity(uni), s),
    curricula: (uni, s) => replay(curricula as CurriculumSummary[], [], () => noUniversity(uni), s),
    curriculum: (uni, code, s) =>
      replay(
        curriculum as CurriculumDetail,
        { ...(curriculum as CurriculumDetail), blocks: [] },
        () => noCurriculum(uni, code),
        s,
      ),
    curriculumCourses: (uni, code, s) =>
      replay(curriculumCourses as CurriculumCourses, emptyCourses(code), () => noCurriculum(uni, code), s),
    dataIssues: (s) => replay(dataIssues as DataIssues, { count: 0, issues: [] }, internal, s),
    prerequisiteGraph: (uni, code, s) =>
      replay(
        graph as PrerequisiteGraph,
        { curriculum_code: code, nodes: [], edges: [] },
        () => noCurriculum(uni, code),
        s,
      ),
    profile: (_ref, _q, s) =>
      replay(
        profile as StudentProfile,
        { ...(profile as StudentProfile), blocks: [], outstanding_courses: [], interests: [], gpa: null },
        noStudent,
        s,
      ),
    courseStatus: (_ref, _q, s) => replay(courseStatus as CourseStatus, emptyStatus, noStudent, s),
    recommendations: (_ref, _q, s) =>
      replay(recommendations as Recommendations, emptyRecommendations, noStudent, s),
    recommend: async (_ref, body, s) => {
      const data = await replay(recommendations as Recommendations, emptyRecommendations, noStudent, s);
      return { ...data, what_if: whatIf(body) };
    },
    planCheck: (_ref, _body, s) =>
      replay(
        planCheck as PlanCheck,
        { ...(planCheck as PlanCheck), total_credits: 0, valid: true, violations: [] },
        noStudent,
        s,
      ),
  };
}
