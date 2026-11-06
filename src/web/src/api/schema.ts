// Tên gọn cho các kiểu sinh từ docs/api/openapi.json. Không khai báo tay kiểu phản hồi ở đây:
// đổi hợp đồng thì chạy `npm run gen:api`, mọi chỗ dùng sẽ tự cập nhật theo.
import type { components, operations } from "./types";

type Schemas = components["schemas"];

/** Kiểu body của phản hồi 200 cho một operation trong openapi.json. */
export type OkBody<Op extends keyof operations> = operations[Op] extends {
  responses: { 200: { content: { "application/json": infer T } } };
}
  ? T
  : never;

export type Health = OkBody<"get_health_v1_health_get">;
export type Meta = Schemas["MetaOut"];
export type University = Schemas["UniversityOut"];
export type Term = Schemas["TermOut"];
export type CurriculumSummary = Schemas["CurriculumSummaryOut"];
export type CurriculumDetail = Schemas["CurriculumDetailOut"];
export type CurriculumBlock = Schemas["CurriculumBlockOut"];
export type CurriculumCourses = Schemas["CurriculumCoursesOut"];
export type CurriculumCourse = Schemas["CourseItemOut"];
export type DataIssues = Schemas["DataIssuesOut"];
export type DataIssue = Schemas["DataIssueItemOut"];
export type ErrorResponse = Schemas["ErrorResponse"];

/** §4.2: các nhóm nối bằng VÀ, các mã trong một nhóm nối bằng HOẶC. */
export type PrerequisiteGroups = CurriculumCourse["prerequisite_groups"];

export type StudentProfile = Schemas["StudentProfileOut"];
export type StudentProfileBlock = Schemas["StudentProfileBlockOut"];
export type CourseStatus = Schemas["CourseStatusOut"];
export type CourseStatusItem = Schemas["CourseStatusItemOut"];
export type CourseStatusSummary = Schemas["CourseStatusSummaryOut"];
export type Recommendations = Schemas["RecommendationsOut"];
export type RecommendationItem = Schemas["RecommendationItemOut"];
export type RecommendationReason = Schemas["RecommendationReasonOut"];
export type RecommendationBody = Schemas["RecommendationBodyIn"];
export type Assumption = Schemas["AssumptionIn"];
export type Swap = Schemas["SwapIn"];
export type PlanCheck = Schemas["PlanCheckOut"];
export type PlanCheckBody = Schemas["PlanCheckBodyIn"];
export type PlanViolation = Schemas["PlanViolationOut"];
export type PrerequisiteGraph = Schemas["PrerequisiteGraphOut"];
export type GraphNode = Schemas["PrerequisiteGraphNode"];
export type GraphEdge = Schemas["PrerequisiteGraphEdge"];

/** Sáu khóa trọng số của §6.6, theo thứ tự bảng mặc định. */
export const WEIGHT_KEYS = [
  "outstanding_retake",
  "overdue",
  "on_time",
  "unlocks",
  "strong_topic",
  "interest",
] as const;
export type WeightKey = (typeof WEIGHT_KEYS)[number];
