import {useCallback, useEffect, useState, type ReactNode} from "react";
import {ApiError, api} from "../../api/client";
import {Button, Card, Chip, Metric, ScreenState, SectionTitle} from "../../components/ui";
import {fmtDate, fmtDateLong, fmtDuration, fmtTime, todayVN} from "../../lib/date-vn";
import {fmtMoney} from "../../lib/format";
import {hapticImpact, hapticNotify} from "../../lib/haptic";
import type {
  ManagedEmployee,
  PayrollApproveResult,
  PayrollDetail,
  PayrollSession,
  PayrollSummary,
  RateHistory,
  ReviewItem,
  WorkingNowItem,
} from "../../types/api";

function useBackButton(active: boolean, onBack: () => void) {
  useEffect(() => {
    const back = window.Telegram?.WebApp?.BackButton;
    if (!back) return;
    if (!active) {
      back.hide();
      return;
    }
    back.show();
    back.onClick(onBack);
    return () => {
      back.offClick(onBack);
      back.hide();
    };
  }, [active, onBack]);
}

function errorText(error: unknown) {
  return error instanceof Error ? error.message : "Không thể tải dữ liệu. Vui lòng thử lại.";
}

function pendingText(reason: PayrollSummary["pending_reason"]) {
  if (reason === "open_session") return "Có phiên đang mở, sẽ vào đợt sau";
  if (reason === "unreviewed_gps") return "Có cờ GPS chưa xử lý";
  if (reason === "forgot_checkout") return "Có phiên quên ra ca";
  return "Sẵn sàng duyệt";
}

function reviewType(row: ReviewItem): "gps" | "forgot" {
  return row.status === "needs_review" || row.review_reason === "forgot_checkout" ? "forgot" : "gps";
}

function sessionTime(row: {check_in_at: string; check_out_at: string | null; minutes: number | null}) {
  return `${fmtTime(row.check_in_at)}–${fmtTime(row.check_out_at)} · ${row.minutes ?? "—"} phút`;
}

export function WorkingScreen() {
  const [rows, setRows] = useState<WorkingNowItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      setRows(await api.get<WorkingNowItem[]>("/working-now"));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 60_000);
    return () => window.clearInterval(id);
  }, [load]);

  if (loading) return <ScreenState kind="loading" title="Đang tải người trong ca" />;
  if (error) return <ScreenState kind="error" title="Không tải được danh sách" message={error} onRetry={load} />;

  return (
    <div className="screen-stack">
      <SectionTitle eyebrow="Đang làm" title={`Trong ca (${rows.length})`} />
      {rows.length === 0 && <ScreenState kind="empty" title="Chưa có ai trong ca" message="Danh sách sẽ tự làm mới mỗi 60 giây." />}
      {rows.map((row) => {
        return (
          <Card key={row.session_id} className="manager-card">
            <div className="manager-row">
              <div>
                <b>{row.full_name}</b>
                <small>{row.code} · Vào ca {fmtTime(row.check_in_at)}</small>
              </div>
              <Chip tone={row.is_outside ? "warning" : "success"}>
                {row.is_outside ? `Ngoài xưởng (${Math.round(row.check_in_distance_m ?? 0)} m)` : "Trong xưởng"}
              </Chip>
            </div>
            <div className="manager-time">{fmtDuration(row.minutes_worked)}</div>
          </Card>
        );
      })}
    </div>
  );
}

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

export function PayrollScreen() {
  const [date, setDate] = useState(todayVN());
  const [rows, setRows] = useState<PayrollSummary[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [detailId, setDetailId] = useState<number | null>(new URLSearchParams(window.location.search).get("scenario") === "manager_payroll_a_detail" ? 1 : null);
  const [confirm, setConfirm] = useState(new URLSearchParams(window.location.search).get("scenario") === "manager_payroll_confirm");
  const [result, setResult] = useState<PayrollApproveResult[] | null>(new URLSearchParams(window.location.search).get("scenario") === "manager_payroll_done" ? [
    {employee_id: 2, batch_id: 20, batch_no: 1, amount: 224000},
    {employee_id: 4, batch_id: 21, batch_no: 1, amount: 168000},
  ] : null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useBackButton(Boolean(detailId || confirm || result), () => { setDetailId(null); setConfirm(false); setResult(null); });

  const load = useCallback(async () => {
    try {
      setError(null);
      setRows(await api.get<PayrollSummary[]>(`/payroll?date=${date}`));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => void load(), [load]);

  const selected = rows.filter((row) => selectedIds.includes(row.employee_id));
  const totals = selected.reduce((acc, row) => ({minutes: acc.minutes + row.eligible_minutes, amount: acc.amount + row.pending_amount}), {minutes: 0, amount: 0});

  const approve = async () => {
    setBusy(true);
    try {
      const data = await api.post<PayrollApproveResult[]>("/payroll/approve", {date, employee_ids: selectedIds});
      hapticNotify("success");
      setResult(data);
      setConfirm(false);
      setSelectedIds([]);
      await load();
    } catch (err) {
      hapticNotify("error");
      if (err instanceof ApiError && err.code === "NO_ELIGIBLE_SESSIONS") {
        setRows([]);
        setConfirm(false);
      } else {
        setError(errorText(err));
      }
    } finally {
      setBusy(false);
    }
  };

  if (detailId) return <PayrollDetailScreen employeeId={detailId} date={date} onBack={() => setDetailId(null)} />;
  if (result) return <PayrollResultScreen result={result} rows={rows} onBack={() => setResult(null)} />;
  if (confirm) return <PayrollConfirmScreen rows={selected} totals={totals} busy={busy} onCancel={() => setConfirm(false)} onApprove={approve} />;
  if (loading) return <ScreenState kind="loading" title="Đang tải dữ liệu duyệt lương" />;
  if (error) return <ScreenState kind="error" title="Không tải được duyệt lương" message={error} onRetry={load} />;

  return (
    <div className="screen-stack payroll-screen">
      <SectionTitle
        eyebrow="Duyệt lương"
        title={fmtDateLong(`${date}T12:00:00+07:00`)}
        action={<DateNav value={date} onChange={setDate} />}
      />
      {rows.length === 0 && <ScreenState kind="empty" title="Không có dữ liệu để duyệt" message="Hiện không có phiên nào đủ điều kiện duyệt lương." />}
      {rows.map((row) => {
        const checked = selectedIds.includes(row.employee_id);
        return (
          <Card key={row.employee_id} className="manager-card clickable-card" onClick={() => setDetailId(row.employee_id)}>
            <div className="manager-row">
              <div>
                <b>{row.full_name}</b>
                <small>{row.code} · Đơn giá {fmtMoney(row.hourly_rate ?? 0)}/giờ</small>
              </div>
              {row.can_approve ? (
                <input
                  aria-label={`Chọn ${row.full_name}`}
                  type="checkbox"
                  checked={checked}
                  onClick={(event) => event.stopPropagation()}
                  onChange={() => setSelectedIds((ids) => checked ? ids.filter((id) => id !== row.employee_id) : [...ids, row.employee_id])}
                />
              ) : <Chip tone="success">Đã trả hết</Chip>}
            </div>
            <div className="mini-grid">
              <Metric label="Chờ duyệt" value={fmtMoney(row.pending_amount)} tone={row.pending_amount ? "warning" : "success"} />
              <Metric label="Đã trả hôm nay" value={fmtMoney(row.paid_amount)} />
            </div>
            <p className="muted">{pendingText(row.pending_reason)}</p>
          </Card>
        );
      })}
      <div className="sticky-action">
        <b>Đã chọn {selected.length} nhân viên · {totals.minutes} phút · {fmtMoney(totals.amount)}</b>
        <Button tone="danger" disabled={!selected.length} onClick={() => setConfirm(true)}>Duyệt</Button>
      </div>
    </div>
  );
}

function DateNav({value, onChange}: {value: string; onChange: (value: string) => void}) {
  const shift = (days: number) => {
    const next = new Date(`${value}T12:00:00+07:00`);
    next.setDate(next.getDate() + days);
    onChange(todayVN(next));
  };
  return (
    <div className="date-nav">
      <button onClick={() => shift(-1)}>‹</button>
      <button onClick={() => shift(1)}>›</button>
    </div>
  );
}

function PayrollConfirmScreen({rows, totals, busy, onCancel, onApprove}: {rows: PayrollSummary[]; totals: {minutes: number; amount: number}; busy: boolean; onCancel: () => void; onApprove: () => void}) {
  return (
    <div className="screen-stack">
      <Card>
        <SectionTitle eyebrow="Xác nhận duyệt" title="Khóa các phiên đã chọn?" />
        <p className="muted">Sau khi duyệt, dữ liệu phiên sẽ bị khóa vĩnh viễn và không thể chỉnh sửa.</p>
        <div className="session-list">
          {rows.map((row) => <div key={row.employee_id} className="session-row"><b>{row.full_name}</b><strong>{fmtMoney(row.pending_amount)}</strong></div>)}
        </div>
        <Metric label={`Tổng ${totals.minutes} phút`} value={fmtMoney(totals.amount)} tone="warning" />
        <div className="action-row">
          <Button tone="secondary" onClick={onCancel}>Hủy</Button>
          <Button tone="danger" busy={busy} onClick={onApprove}>Xác nhận duyệt</Button>
        </div>
      </Card>
    </div>
  );
}

function PayrollResultScreen({result, rows, onBack}: {result: PayrollApproveResult[]; rows: PayrollSummary[]; onBack: () => void}) {
  const nameOf = (id: number) => rows.find((row) => row.employee_id === id)?.full_name || `NV #${id}`;
  return (
    <div className="screen-stack">
      <Card>
        <SectionTitle eyebrow="Đã duyệt" title={`${result.length} đợt lương`} />
        {result.map((item) => <div key={item.batch_id} className="session-row"><span>{nameOf(item.employee_id)} · Đợt {item.batch_no}</span><strong>{fmtMoney(item.amount)}</strong></div>)}
        <Button onClick={onBack}>Quay lại danh sách</Button>
      </Card>
    </div>
  );
}

function PayrollDetailScreen({employeeId, date, onBack}: {employeeId: number; date: string; onBack: () => void}) {
  const [detail, setDetail] = useState<PayrollDetail | null>(null);
  const [edit, setEdit] = useState<PayrollSession | null>(new URLSearchParams(window.location.search).get("scenario") === "manager_session_edit" ? null : null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.get<PayrollDetail>(`/payroll/${employeeId}?date=${date}`);
      setDetail(data);
      if (new URLSearchParams(window.location.search).get("scenario") === "manager_session_edit") {
        setEdit(data.sessions.find((row) => !row.is_locked) ?? data.sessions[0]);
      }
    } catch (err) {
      setError(errorText(err));
    }
  }, [date, employeeId]);

  useEffect(() => void load(), [load]);

  if (edit) return <EditSessionScreen row={edit} onBack={() => setEdit(null)} onDone={() => { setEdit(null); void load(); }} />;
  if (error) return <ScreenState kind="error" title="Không tải được chi tiết" message={error} onRetry={load} />;
  if (!detail) return <ScreenState kind="loading" title="Đang tải chi tiết lương" />;

  return (
    <div className="screen-stack">
      <Button tone="ghost" className="back-button" onClick={onBack}>← Quay lại</Button>
      <Card>
        <SectionTitle eyebrow={detail.code} title={detail.full_name} />
        <div className="mini-grid">
          <Metric label="Tổng ngày" value={fmtMoney(detail.day_total_rounded)} />
          <Metric label="Chờ duyệt" value={fmtMoney(detail.pending_amount)} tone="warning" />
        </div>
        {detail.batches.map((batch) => (
          <div className="history-block history-block--paid" key={batch.id}>
            <div className="history-block__head"><b>🔒 Đợt {batch.batch_no} · Đã trả</b><strong>{fmtMoney(batch.amount)}</strong></div>
            {detail.sessions.filter((row) => row.pay_batch_id === batch.id).map((row) => <SessionLine key={row.id} row={row} />)}
          </div>
        ))}
        <div className="history-block">
          <div className="history-block__head"><b>Chờ duyệt</b><strong>{fmtMoney(detail.pending_amount)}</strong></div>
          {detail.sessions.filter((row) => !row.pay_batch_id && row.status === "closed").map((row) => (
            <SessionLine key={row.id} row={row} action={<Button tone="secondary" onClick={() => setEdit(row)}>Sửa phiên</Button>} />
          ))}
          {detail.sessions.filter((row) => row.status === "open").map((row) => <p key={row.id} className="muted">Phiên đang mở từ {fmtTime(row.check_in_at)} · sẽ vào đợt sau.</p>)}
        </div>
      </Card>
    </div>
  );
}

function SessionLine({row, action}: {row: PayrollSession; action?: ReactNode}) {
  return (
    <div className="session-row">
      <div><b>{sessionTime(row)}</b><small>{row.flags.includes("gps_out_of_range") ? "Ngoài xưởng" : "GPS bình thường"}</small></div>
      {action || (row.is_locked ? <Chip tone="success">Đã khóa</Chip> : <Chip tone="warning">Chờ duyệt</Chip>)}
    </div>
  );
}

function EditSessionScreen({row, onBack, onDone}: {row: PayrollSession; onBack: () => void; onDone: () => void}) {
  const [start, setStart] = useState(fmtTime(row.check_in_at));
  const [end, setEnd] = useState(fmtTime(row.check_out_at));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const startIso = `${row.work_date}T${start}:00+07:00`;
  const endIso = `${row.work_date}T${end}:00+07:00`;
  const minutes = Math.max(0, Math.floor((new Date(endIso).getTime() - new Date(startIso).getTime()) / 60000));

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.patch(`/review/${row.id}`, {check_in_time: startIso, check_out_time: endIso, reason});
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
        <SectionTitle eyebrow="Sửa phiên" title={fmtDateLong(row.check_in_at)} />
        <div className="two-col">
          <label className="form-field">Giờ vào<input type="time" value={start} onChange={(event) => setStart(event.target.value)} /></label>
          <label className="form-field">Giờ ra<input type="time" value={end} onChange={(event) => setEnd(event.target.value)} /></label>
        </div>
        <Metric label="Thời lượng tự tính" value={`${minutes} phút`} />
        <label className="form-field">Lý do điều chỉnh<textarea maxLength={200} value={reason} onChange={(event) => setReason(event.target.value)} /></label>
        {error && <p className="form-error">{error}</p>}
        <Button disabled={minutes <= 0 || reason.trim().length < 5} busy={busy} onClick={submit}>Lưu thay đổi</Button>
      </Card>
    </div>
  );
}

export function EmployeesScreen() {
  const [rows, setRows] = useState<ManagedEmployee[]>([]);
  const [q, setQ] = useState("");
  const [active, setActive] = useState<"all" | "active" | "locked">("all");
  const [screen, setScreen] = useState<"list" | "add" | "detail">(new URLSearchParams(window.location.search).get("scenario") === "manager_employee_add" ? "add" : new URLSearchParams(window.location.search).get("scenario") === "manager_employee_detail" ? "detail" : "list");
  const [selected, setSelected] = useState<ManagedEmployee | null>(null);
  const [invite, setInvite] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useBackButton(screen !== "list", () => { setScreen("list"); setSelected(null); setInvite(null); });

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (active !== "all") params.set("active", active === "active" ? "true" : "false");
      const data = await api.get<ManagedEmployee[]>(`/employees${params.toString() ? `?${params}` : ""}`);
      setRows(data);
      if (!selected) setSelected(data[0] ?? null);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }, [active, q, selected]);

  useEffect(() => void load(), [load]);

  if (screen === "add") return <EmployeeAddScreen onBack={() => setScreen("list")} onCreated={(url) => setInvite(url)} invite={invite} />;
  if (screen === "detail") return <EmployeeDetailScreen employee={selected || rows[0]} onBack={() => setScreen("list")} onChanged={load} />;
  if (loading) return <ScreenState kind="loading" title="Đang tải nhân viên" />;
  if (error) return <ScreenState kind="error" title="Không tải được nhân viên" message={error} onRetry={load} />;

  const toggleLock = async (row: ManagedEmployee) => {
    if (row.is_active && !window.confirm(`Khóa tài khoản ${row.full_name}?`)) return;
    try {
      const updated = row.is_active
        ? await api.post<ManagedEmployee>(`/employees/${row.id}/lock`)
        : await api.post<ManagedEmployee>(`/employees/${row.id}/unlock`);
      setRows((items) => items.map((item) => item.id === row.id ? updated : item));
      hapticNotify("success");
    } catch (err) {
      hapticNotify("error");
      setError(errorText(err));
    }
  };

  return (
    <div className="screen-stack">
      <SectionTitle eyebrow="Nhân viên" title="Danh sách nhân viên" action={<Button className="small-button" onClick={() => setScreen("add")}>Thêm</Button>} />
      <Card>
        <label className="form-field">Tìm kiếm<input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Tên hoặc mã nhân viên" /></label>
        <div className="segmented">
          <button className={active === "all" ? "active" : ""} onClick={() => setActive("all")}>Tất cả</button>
          <button className={active === "active" ? "active" : ""} onClick={() => setActive("active")}>Đang hoạt động</button>
          <button className={active === "locked" ? "active" : ""} onClick={() => setActive("locked")}>Đã khóa</button>
        </div>
      </Card>
      {rows.map((row) => (
        <Card key={row.id} className="manager-card">
          <div className="manager-row">
            <button className="plain-button" onClick={() => { setSelected(row); setScreen("detail"); }}>
              <b>{row.full_name}</b>
              <small>{row.code} · {fmtMoney(row.current_hourly_rate ?? 0)}/giờ</small>
            </button>
            <button type="button" className={`switch ${row.is_active ? "on" : ""}`} aria-label={row.is_active ? "Khóa" : "Mở khóa"} onClick={() => void toggleLock(row)} />
          </div>
          <div className="chip-row">
            {!row.is_linked && <Chip tone="warning">Chưa liên kết</Chip>}
            {row.has_open_session && <Chip tone="info">Đang trong ca</Chip>}
            {!row.is_active && <Chip tone="danger">Đã khóa</Chip>}
          </div>
        </Card>
      ))}
    </div>
  );
}

function EmployeeAddScreen({onBack, onCreated, invite}: {onBack: () => void; onCreated: (url: string) => void; invite: string | null}) {
  const [form, setForm] = useState({code: "", full_name: "", hourly_rate: 30000, effective_from: todayVN()});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setField = (key: keyof typeof form, value: string | number) => setForm((current) => ({...current, [key]: value}));
  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const created = await api.post<ManagedEmployee>("/employees", form);
      hapticNotify("success");
      onCreated(created.invite_url || "");
    } catch (err) {
      hapticNotify("error");
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };
  const share = () => invite && window.Telegram?.WebApp?.openTelegramLink?.(`https://t.me/share/url?url=${encodeURIComponent(invite)}`);
  return (
    <div className="screen-stack">
      <Button tone="ghost" className="back-button" onClick={onBack}>← Quay lại</Button>
      <Card>
        <SectionTitle eyebrow="Thêm nhân viên" title="Tạo hồ sơ và link mời" />
        <label className="form-field">Mã nhân viên<input value={form.code} onChange={(event) => setField("code", event.target.value)} /></label>
        <label className="form-field">Họ tên<input value={form.full_name} onChange={(event) => setField("full_name", event.target.value)} /></label>
        <label className="form-field">Đơn giá giờ<input type="number" value={form.hourly_rate} onChange={(event) => setField("hourly_rate", Number(event.target.value))} /></label>
        <label className="form-field">Hiệu lực từ ngày<input type="date" min={todayVN()} value={form.effective_from} onChange={(event) => setField("effective_from", event.target.value)} /></label>
        {error && <p className="form-error">{error}</p>}
        <Button busy={busy} onClick={submit}>Tạo nhân viên</Button>
        {invite && (
          <div className="invite-box">
            <b>Link mời</b>
            <p>{invite}</p>
            <div className="action-row">
              <Button tone="secondary" onClick={() => void navigator.clipboard?.writeText(invite)}>Sao chép</Button>
              <Button onClick={share}>Chia sẻ qua Telegram</Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

function EmployeeDetailScreen({employee, onBack, onChanged}: {employee: ManagedEmployee | null; onBack: () => void; onChanged: () => void}) {
  const [rates, setRates] = useState<RateHistory[]>([]);
  const [rate, setRate] = useState({hourly_rate: 32000, effective_from: todayVN()});
  const [invite, setInvite] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!employee) return;
    try {
      setRates(await api.get<RateHistory[]>(`/employees/${employee.id}/rates`));
    } catch (err) {
      setError(errorText(err));
    }
  }, [employee]);

  useEffect(() => void load(), [load]);

  if (!employee) return <ScreenState kind="empty" title="Chưa chọn nhân viên" />;

  const saveRate = async () => {
    setBusy(true);
    try {
      await api.post(`/employees/${employee.id}/rates`, rate);
      hapticNotify("success");
      await load();
      onChanged();
    } catch (err) {
      hapticNotify("error");
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const regenerate = async () => {
    const data = await api.post<ManagedEmployee>(`/employees/${employee.id}/invite`);
    setInvite(data.invite_url || null);
  };

  return (
    <div className="screen-stack">
      <Button tone="ghost" className="back-button" onClick={onBack}>← Quay lại</Button>
      <Card>
        <SectionTitle eyebrow={employee.code} title={employee.full_name} />
        <Metric label="Đơn giá hiện tại" value={`${fmtMoney(employee.current_hourly_rate ?? 0)}/giờ`} />
        <SectionTitle title="Thiết lập đơn giá giờ" />
        <div className="two-col">
          <label className="form-field">Nhập đơn giá (giờ)<input type="number" value={rate.hourly_rate} onChange={(event) => setRate({...rate, hourly_rate: Number(event.target.value)})} /></label>
          <label className="form-field">Hiệu lực từ ngày<input type="date" min={todayVN()} value={rate.effective_from} onChange={(event) => setRate({...rate, effective_from: event.target.value})} /></label>
        </div>
        {error && <p className="form-error">{error}</p>}
        <Button busy={busy} onClick={saveRate}>Lưu đơn giá</Button>
        <div className="history-block">
          <b>Lịch sử đơn giá</b>
          {rates.map((item) => <div className="session-row" key={item.id}><span>{fmtMoney(item.hourly_rate)}/giờ</span><small>Từ {fmtDate(`${item.effective_from}T12:00:00+07:00`)}</small></div>)}
        </div>
        {!employee.is_linked && <Button tone="secondary" onClick={() => void regenerate()}>Tạo lại link mời</Button>}
        {invite && <p className="invite-box">{invite}</p>}
      </Card>
    </div>
  );
}
