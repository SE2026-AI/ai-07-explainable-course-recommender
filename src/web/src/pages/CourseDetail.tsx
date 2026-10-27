import { Link, useParams } from "react-router-dom";
import type { CatalogCourse, Graph } from "../api/types";
import type { WhyNotResult } from "../lib/presentation";
import { WhyNot } from "../components/ExplanationPanel/WhyNot";
interface Props {
  courses: CatalogCourse[];
  graph: Graph | null;
  onAsk(id: string): Promise<WhyNotResult | null>;
}
export function CourseDetail({ courses, graph, onAsk }: Props) {
  const { id } = useParams();
  const course = courses.find((c) => c.course_id === id);
  if (!course)
    return (
      <section className="panel">
        <h2>Không tìm thấy môn {id}</h2>
        <Link to="/results">Quay lại kết quả</Link>
      </section>
    );
  return (
    <section
      className="panel course-detail"
      aria-label={`Chi tiết ${course.course_id}`}
    >
      <Link to="/results">Quay lại kết quả</Link>
      <h2>
        {course.course_id} · {course.title}
      </h2>
      <p>
        {course.credits} tín chỉ · {course.workload_hours_per_week ?? "?"}{" "}
        giờ/tuần
      </p>
      <h3>Môn tiên quyết bắt buộc</h3>
      {course.mandatory_prerequisites.length ? (
        <ul>
          {course.mandatory_prerequisites.map((p) => (
            <li key={p}>
              <Link to={`/course/${p}`}>
                {p} · {courses.find((c) => c.course_id === p)?.title}
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p>Không có môn tiên quyết.</p>
      )}
      <h3>Chuẩn bị khuyến nghị</h3>
      <p>{course.recommended_preparation?.join(", ") || "Không có"}</p>
      <h3>Kỳ mở môn</h3>
      <p>{course.available_terms.join(", ") || "Chưa có thông tin"}</p>
      {graph && (
        <>
          <h3>Môn học tiếp theo</h3>
          <ul>
            {graph.edges
              .filter((e) => e.prerequisite_course_id === id)
              .map((e) => (
                <li key={e.dependent_course_id}>
                  <Link to={`/course/${e.dependent_course_id}`}>
                    {e.dependent_course_id}
                  </Link>
                </li>
              ))}
          </ul>
        </>
      )}
      <WhyNot key={id} courses={[course]} disabled={false} onAsk={onAsk} />
    </section>
  );
}
