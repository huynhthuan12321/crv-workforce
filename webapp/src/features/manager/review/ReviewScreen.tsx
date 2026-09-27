import {useCallback, useEffect, useState} from "react";
import {ApiError, api} from "../../../api/client";
import {Button, Card, Chip, Metric, ScreenState, SectionTitle} from "../../../components/ui";
import {fmtDate, fmtDateLong, fmtTime} from "../../../lib/date-vn";
import {gpsLabel} from "../../../lib/gps-label";
import {hapticImpact, hapticNotify} from "../../../lib/haptic";
import type {CheckoutBounds, ReviewItem, WorkSession} from "../../../types/api";
import {errorText, reviewType, sessionTime, useBackButton} from "../shared";

export function ReviewScreen({initialFilter = "all"}: {initialFilter?: "all" | "gps" | "forgot"} = {}) {
  const [filter, setFilter] = useState<"all" | "gps" | "forgot">(initialFilter);
  const [mode, setMode] = useState<"pending" | "resolved">(
    new URLSearchParams(window.location.search).get("scenario") === "manager_review_resolved" ? "resolved" : "pending",
  );
  const [pending, setPending] = useState<ReviewItem[]>([]);
  const [resolved, setResolved] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ReviewItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const scenario = new URLSearchParams(window.location.search).get("scenario");
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
  useEffect(() => setFilter(initialFilter), [initialFilter]);
  useEffect(() => {
    if (scenario === "manager_review_close" && !selected) {
      const forgot = pending.find((row) => reviewType(row) === "forgot");
      if (forgot) setSelected(forgot);
    }
  }, [pending, scenario, selected]);

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
            {key === "all" ? `Tất cả (${pending.length})` : key === "gps" ? `Vị trí (${gpsCount})` : `Quên ra ca (${forgotCount})`}
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
              <Chip tone={type === "gps" ? "warning" : "danger"}>{type === "gps" ? "Vị trí" : "Quên ra ca"}</Chip>
            </div>
            {type === "gps" ? (
              <p className="muted">{gpsLabel(row)}</p>
            ) : (
              <p className="muted">Cần nhập giờ ra và lý do xử lý.</p>
            )}
            {mode === "pending" && type === "gps" && <Button onClick={() => void markFlags(row)}>Đã xem</Button>}
            {mode === "pending" && type === "forgot" && <Button onClick={() => setSelected(row)}>Xử lý phiên</Button>}
            {mode === "resolved" && (
              <p className="muted">Đã xử lý bởi {row.resolved_by_name || "—"} lúc {fmtTime(row.resolved_at)} · {row.resolved_action === "flags_reviewed" ? "Đã xem vị trí" : "Đóng phiên quên"}</p>
            )}
            {mode === "resolved" && row.reason && <p className="muted">Lý do: {row.reason}</p>}
          </Card>
        );
      })}
    </div>
  );
}

function CloseForgottenScreen({row, onBack, onDone}: {row: ReviewItem; onBack: () => void; onDone: () => void}) {
  const [time, setTime] = useState("");
  const [reason, setReason] = useState("");
  const [bounds, setBounds] = useState<CheckoutBounds | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const checkOutIso = time ? `${row.work_date}T${time}:00+07:00` : "";
  const minutes = time ? Math.max(0, Math.floor((new Date(checkOutIso).getTime() - new Date(row.check_in_at).getTime()) / 60000)) : 0;
  const invalid = !time || minutes <= 0 || reason.trim().length < 5;

  useEffect(() => {
    let active = true;
    api.get<CheckoutBounds>(`/review/${row.id}/checkout-bounds`)
      .then((data) => { if (active) setBounds(data); })
      .catch((err) => { if (active) setError(checkoutErrorText(err)); });
    return () => { active = false; };
  }, [row.id]);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/review/${row.id}/close`, {check_out_time: checkOutIso, reason});
      hapticNotify("success");
      onDone();
    } catch (err) {
      hapticNotify("error");
      setError(checkoutErrorText(err));
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
        {bounds && <SameDaySessions sessions={bounds.sessions} />}
        <label className="form-field">
          Giờ ra
          <input
            type="time"
            required
            min={bounds ? fmtTime(bounds.min_check_out) : undefined}
            max={bounds ? fmtTime(bounds.max_check_out) : undefined}
            value={time}
            onChange={(event) => setTime(event.target.value)}
          />
          {bounds && <small>Chọn từ {fmtTime(bounds.min_check_out)} đến {fmtTime(bounds.max_check_out)}. Không chọn giờ tương lai hoặc chồng phiên khác.</small>}
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

function SameDaySessions({sessions}: {sessions: WorkSession[]}) {
  if (sessions.length === 0) return <p className="muted">Không có phiên khác trong ngày.</p>;
  return (
    <div className="session-list">
      <b>Phiên khác cùng ngày</b>
      {sessions.map((session) => (
        <div className="session-row" key={session.id}>
          <span>{fmtDate(session.check_in_at)} · {fmtTime(session.check_in_at)}–{session.check_out_at ? fmtTime(session.check_out_at) : "đang mở"}</span>
          <Chip tone={session.status === "open" ? "warning" : "neutral"}>{session.status === "open" ? "Đang mở" : session.status === "needs_review" ? "Cần xử lý" : "Đã đóng"}</Chip>
        </div>
      ))}
    </div>
  );
}

function checkoutErrorText(error: unknown) {
  if (error instanceof ApiError) {
    const max = typeof error.details?.max_check_out === "string" ? fmtTime(error.details.max_check_out) : null;
    const overlap = typeof error.details?.overlap === "object" && error.details?.overlap
      ? error.details.overlap as {check_in_at?: string; check_out_at?: string | null}
      : null;
    if (error.code === "CHECKOUT_IN_FUTURE") {
      return `Giờ ra không được ở tương lai${max ? `. Muộn nhất có thể chọn ${max}` : ""}.`;
    }
    if (error.code === "SESSION_OVERLAP") {
      const overlapText = overlap?.check_in_at
        ? ` Phiên bị chồng: ${fmtTime(overlap.check_in_at)}–${overlap.check_out_at ? fmtTime(overlap.check_out_at) : "đang mở"}.`
        : "";
      return `Giờ ra bị chồng với phiên khác${max ? `. Muộn nhất có thể chọn ${max}` : ""}.${overlapText}`;
    }
  }
  return errorText(error);
}
