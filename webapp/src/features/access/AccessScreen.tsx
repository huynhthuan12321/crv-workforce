import {Button, Card} from "../../components/ui";
import {errorMessages, errorTitles} from "../../app/labels";

export function AccessScreen({code, onRetry}: {code: string; onRetry: () => void}) {
  const title = errorTitles[code] || "Không thể mở ứng dụng";
  const message = errorMessages[code] || "Có lỗi xảy ra khi kết nối tới máy chủ. Vui lòng thử lại.";
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
