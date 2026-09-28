import {describe, expect, it} from "vitest";
import {formatLocationInUseMessage} from "./EmployeesScreen";

describe("location in-use message", () => {
  it("includes current assignments and open sessions", () => {
    expect(formatLocationInUseMessage("Kho A", {
      current_assignments: [{id: 1}, {id: 2}],
      open_sessions: [{id: 10}],
    })).toBe("Không thể ngừng dùng Kho A: còn 2 nhân viên đang phân công, 1 ca đang mở. Chuyển nhân viên sang kho khác trước.");
  });

  it("omits open session text when there is no open session", () => {
    expect(formatLocationInUseMessage("Kho B", {
      current_assignments: 3,
      open_sessions: 0,
    })).toBe("Không thể ngừng dùng Kho B: còn 3 nhân viên đang phân công. Chuyển nhân viên sang kho khác trước.");
  });
});
