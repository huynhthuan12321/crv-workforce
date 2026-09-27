import {errorMessages, errorTitles} from "../../app/labels";
import {Button, Card} from "../../components/ui";

type AccessError = {
  code: string;
  status?: number;
};

const accessErrorMessages: Record<string, string> = {
  INVITE_INVALID: "Link mời không hợp lệ hoặc đã hết hạn. Vui lòng xin quản lý gửi link mới.",
  INVITE_EXPIRED: "Link mời không hợp lệ hoặc đã hết hạn. Vui lòng xin quản lý gửi link mới.",
  INVITE_USED: "Link mời này đã được dùng. Nếu bạn đã liên kết, hãy mở app từ nút Chấm công trong bot.",
  NOT_REGISTERED: "Tài khoản Telegram này chưa được cấp quyền. Liên hệ quản lý để nhận link mời.",
};

const accessErrorTitles: Record<string, string> = {
  INVITE_INVALID: "Link mời không hợp lệ",
  INVITE_EXPIRED: "Link mời đã hết hạn",
  INVITE_USED: "Link mời đã được dùng",
  NOT_REGISTERED: "Chưa được cấp quyền",
};

export function accessMessageForError({code, status}: AccessError) {
  if (accessErrorMessages[code]) return accessErrorMessages[code];
  if (code === "NETWORK_ERROR" || (status && status >= 500)) return "Không kết nối được máy chủ";
  return errorMessages[code] || "Không thể mở ứng dụng. Vui lòng thử lại hoặc liên hệ quản lý.";
}

export function accessTitleForError({code}: AccessError) {
  return accessErrorTitles[code] || errorTitles[code] || "Không thể mở ứng dụng";
}

export function AccessScreen({code, status, onRetry}: {code: string; status?: number; onRetry: () => void}) {
  const title = accessTitleForError({code, status});
  const message = accessMessageForError({code, status});
  const isExpired = code === "INITDATA_EXPIRED" || code === "SESSION_EXPIRED";

  return (
    <main className="app-shell app-shell--center">
      <Card className="access-card">
        <div className="access-card__mark">{code === "ACCOUNT_LOCKED" ? "×" : code === "NOT_REGISTERED" ? "?" : "!"}</div>
        <h1>{title}</h1>
        <p>{message}</p>
        {!isExpired && <Button tone="secondary" onClick={onRetry}>Thử lại</Button>}
      </Card>
    </main>
  );
}
