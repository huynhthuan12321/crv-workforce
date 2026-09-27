import {render, screen} from "@testing-library/react";
import {describe, expect, it, vi} from "vitest";
import {AccessScreen, accessMessageForError} from "./AccessScreen";

describe("AccessScreen", () => {
  const cases = [
    {
      code: "INVITE_INVALID",
      message: "Link mời không hợp lệ hoặc đã hết hạn. Vui lòng xin quản lý gửi link mới.",
    },
    {
      code: "INVITE_EXPIRED",
      message: "Link mời không hợp lệ hoặc đã hết hạn. Vui lòng xin quản lý gửi link mới.",
    },
    {
      code: "INVITE_USED",
      message: "Link mời này đã được dùng. Nếu bạn đã liên kết, hãy mở app từ nút Chấm công trong bot.",
    },
    {
      code: "NOT_REGISTERED",
      message: "Tài khoản Telegram này chưa được cấp quyền. Liên hệ quản lý để nhận link mời.",
    },
  ];

  it.each(cases)("shows business message for $code", ({code, message}) => {
    render(<AccessScreen code={code} onRetry={vi.fn()} />);

    expect(screen.getByText(message)).toBeTruthy();
    expect(screen.queryByText("Không kết nối được máy chủ")).toBeNull();
  });

  it("uses the server connection message for network errors", () => {
    expect(accessMessageForError({code: "NETWORK_ERROR"})).toBe("Không kết nối được máy chủ");
  });

  it("uses the server connection message for 5xx responses", () => {
    expect(accessMessageForError({code: "API_ERROR", status: 502})).toBe("Không kết nối được máy chủ");
  });
});
