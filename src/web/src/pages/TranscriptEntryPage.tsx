import { Link, Navigate, useSearchParams } from "react-router-dom";
import { choiceQuery, isComplete, readChoice } from "../lib/wizard";

/**
 * Bước 4 của wizard. WEB-5 chỉ dựng chỗ đứng và nhận lựa chọn của bước 1–3;
 * danh sách môn, ô điểm và tóm tắt (`POST .../transcript`) làm ở WEB-6.
 */
export function TranscriptEntryPage() {
  const [params] = useSearchParams();
  const choice = readChoice(params);
  if (!isComplete(choice)) return <Navigate to={`/${choiceQuery(choice)}`} replace />;

  return (
    <section className="panel narrow">
      <div className="panel-head">
        <div>
          <h2>Bước 4 · Nhập bảng điểm</h2>
          <p>
            Khung <span className="mono">{choice.curriculum}</span> ({choice.uni}), đã học {choice.semesters} kỳ.
          </p>
        </div>
      </div>
      <p className="banner info">Màn nhập bảng điểm đang được làm (WEB-6, #39).</p>
      <Link to={`/${choiceQuery(choice)}`}>Quay lại sửa lựa chọn</Link>
    </section>
  );
}
