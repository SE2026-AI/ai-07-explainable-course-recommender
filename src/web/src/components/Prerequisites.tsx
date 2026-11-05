import { Fragment } from "react";
import type { PrerequisiteGroups } from "../api/schema";

/**
 * Hiện điều kiện tiên quyết đúng hai tầng của §4.2: các nhóm nối bằng "và",
 * các mã trong cùng một nhóm nối bằng "hoặc". Không làm phẳng thành một danh sách mã.
 */
export function Prerequisites({ groups = [] }: { groups?: PrerequisiteGroups }) {
  if (groups.length === 0) return <span className="muted">Không có</span>;
  return (
    <span className="prereq">
      {groups.map((group, i) => (
        <Fragment key={i}>
          {i > 0 && <strong className="prereq-and"> và </strong>}
          <span className="prereq-group">
            {group.length > 1 && groups.length > 1 && "("}
            {group.map((code, j) => (
              <Fragment key={code}>
                {j > 0 && <em className="prereq-or"> hoặc </em>}
                <span className="mono">{code}</span>
              </Fragment>
            ))}
            {group.length > 1 && groups.length > 1 && ")"}
          </span>
        </Fragment>
      ))}
    </span>
  );
}
