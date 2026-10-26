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
