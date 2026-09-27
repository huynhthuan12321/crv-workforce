import {useCallback, useEffect, useState} from "react";
import {ApiError, api} from "../../../api/client";
import {Button, Card, Chip, Metric, ScreenState, SectionTitle} from "../../../components/ui";
import {fmtDate, fmtDateLong, fmtTime} from "../../../lib/date-vn";
import {hapticImpact, hapticNotify} from "../../../lib/haptic";
import type {ReviewItem} from "../../../types/api";
import {errorText, reviewType, sessionTime, useBackButton} from "../shared";

export function ReviewScreen() {
  const [filter, setFilter] = useState<"all" | "gps" | "forgot">("all");
  const [mode, setMode] = useState<"pending" | "resolved">(
    new URLSearchParams(window.location.search).get("scenario") === "manager_review_resolved" ? "resolved" : "pending",
  );
  const [pending, setPending] = useState<ReviewItem[]>([]);
  const [resolved, setResolved] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ReviewItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  useBackButton(Boolean(selected), () => setSelected(null));

  const load = useCallback(async () => {
    try {
      setError(null);
      const suffix = filter === "all" ? "" : `?type=${filter}`;
      const [nextPending, nextResolved] = await Promise.all([
        api.get<ReviewItem[]>(`/review/pending${suffix}`),
        api.get<ReviewItem[]>(`/review/resolved${suffix}`),
      ]);
      setPending(nextPending);
      setResolved(nextResolved);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => void load(), [load]);

  const markFlags = async (row: ReviewItem) => {
    hapticImpact();
    try {
      await api.post(`/review/${row.id}/flags-reviewed`);
      hapticNotify("success");
      await load();
    } catch (err) {
      hapticNotify("error");
      if (err instanceof ApiError && err.code === "ALREADY_HANDLED") {
        const handledBy = String(err.details?.handled_by_name ?? "người khác");
        const handledAt = err.details?.handled_at ? fmtTime(String(err.details.handled_at)) : "";
        setNotice(`Đã xử lý bởi ${handledBy}${handledAt ? ` lúc ${handledAt}` : ""}.`);
        await load();
        return;
      }
      setError(errorText(err));
    }
  };

  if (selected) return <CloseForgottenScreen row={selected} onBack={() => setSelected(null)} onDone={() => { setSelected(null); void load(); }} />;
  if (loading) return <ScreenState kind="loading" title="Đang tải mục cần xử lý" />;
  if (error) return <ScreenState kind="error" title="Không tải được dữ liệu" message={error} onRetry={load} />;

  const source = mode === "pending" ? pending : resolved;
  const gpsCount = pending.filter((row) => reviewType(row) === "gps").length;
  const forgotCount = pending.filter((row) => reviewType(row) === "forgot").length;

  return (
    <div className="screen-stack">
      <SectionTitle eyebrow="Cần xử lý" title="Phiên bất thường" />
      {notice && <Card className="notice-card">{notice}</Card>}
      <div className="segmented">
        {(["all", "gps", "forgot"] as const).map((key) => (
          <button key={key} className={filter === key ? "active" : ""} onClick={() => setFilter(key)}>
            {key === "all" ? `Tất cả (${pending.length})` : key === "gps" ? `GPS (${gpsCount})` : `Quên ra ca (${forgotCount})`}
          </button>
        ))}
      </div>
      <div className="segmented segmented--sub">
        <button className={mode === "pending" ? "active" : ""} onClick={() => setMode("pending")}>Chưa xử lý</button>
        <button className={mode === "resolved" ? "active" : ""} onClick={() => setMode("resolved")}>Đã xử lý</button>
      </div>
      {source.length === 0 && <ScreenState kind="empty" title={mode === "pending" ? "Không còn mục cần xử lý" : "Chưa có mục đã xử lý"} />}
      {source.map((row) => {
        const type = reviewType(row);
        return (
          <Card key={row.id} className="manager-card">
            <div className="manager-row">
              <div>
                <b>{row.employee_name}</b>
                <small>{row.employee_code} · Vào ca {fmtTime(row.check_in_at)}</small>
              </div>
              <Chip tone={type === "gps" ? "warning" : "danger"}>{type === "gps" ? "GPS" : "Quên ra ca"}</Chip>
            </div>
            {type === "gps" ? (
              <p className="muted">Khoảng cách {Math.round(row.check_in_distance_m)} m · Sai số {Math.round(row.check_in_accuracy_m ?? 0)} m</p>
            ) : (
              <p className="muted">Cần nhập giờ ra và lý do xử lý.</p>
            )}
            {mode === "pending" && type === "gps" && <Button onClick={() => void markFlags(row)}>Đã xem</Button>}
            {mode === "pending" && type === "forgot" && <Button onClick={() => setSelected(row)}>Xử lý phiên</Button>}
            {mode === "resolved" && (
              <p className="muted">Đã xử lý bởi {row.resolved_by_name || "—"} lúc {fmtTime(row.resolved_at)} · {row.resolved_action === "flags_reviewed" ? "Đã xem GPS" : "Đóng phiên quên"}</p>
            )}
            {mode === "resolved" && row.reason && <p className="muted">Lý do: {row.reason}</p>}
          </Card>
        );
      })}
    </div>
  );
}

function CloseForgottenScreen({row, onBack, onDone}: {row: ReviewItem; onBack: () => void; onDone: () => void}) {
  const [time, setTime] = useState("20:00");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const checkOutIso = `${row.work_date}T${time}:00+07:00`;
  const minutes = Math.max(0, Math.floor((new Date(checkOutIso).getTime() - new Date(row.check_in_at).getTime()) / 60000));
  const invalid = minutes <= 0 || reason.trim().length < 5;

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/review/${row.id}/close`, {check_out_time: checkOutIso, reason});
      hapticNotify("success");
      onDone();
    } catch (err) {
      hapticNotify("error");
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="screen-stack">
      <Button tone="ghost" className="back-button" onClick={onBack}>← Quay lại</Button>
      <Card>
        <SectionTitle eyebrow="Quên ra ca" title={row.employee_name} />
        <p className="muted">Vào ca {fmtTime(row.check_in_at)} · {fmtDateLong(row.check_in_at)}</p>
        <label className="form-field">
          Giờ ra
          <input type="time" value={time} onChange={(event) => setTime(event.target.value)} />
        </label>
        <Metric label="Thời lượng tự tính" value={`${minutes} phút`} tone={minutes > 0 ? "success" : "warning"} />
        <label className="form-field">
          Lý do xử lý
          <textarea maxLength={200} value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Nhập lý do..." />
          <small>{reason.length}/200 · tối thiểu 5 ký tự</small>
        </label>
        {error && <p className="form-error">{error}</p>}
        <Button tone="danger" disabled={invalid} busy={busy} onClick={submit}>Xác nhận xử lý</Button>
      </Card>
    </div>
  );
}

