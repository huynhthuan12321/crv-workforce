import {useCallback, useEffect, useState, type ReactNode} from "react";
import {ApiError, api} from "../../../api/client";
import {Button, Card, Chip, Metric, ScreenState, SectionTitle} from "../../../components/ui";
import {fmtDateLong, fmtTime, todayVN} from "../../../lib/date-vn";
import {fmtMoney} from "../../../lib/format";
import {hapticNotify} from "../../../lib/haptic";
import type {PayrollApproveResult, PayrollDetail, PayrollSession, PayrollSummary} from "../../../types/api";
import {errorText, pendingText, sessionTime, useBackButton} from "../shared";
export function PayrollScreen() {
  const [date, setDate] = useState(todayVN());
  const [rows, setRows] = useState<PayrollSummary[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>(
    new URLSearchParams(window.location.search).get("scenario") === "manager_payroll_confirm" ? [2, 4] : [],
  );
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
  const approvableIds = rows.filter((row) => row.can_approve).map((row) => row.employee_id);
  const allSelected = approvableIds.length > 0 && approvableIds.every((id) => selectedIds.includes(id));
  const toggleAll = () => setSelectedIds(allSelected ? [] : approvableIds);
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
  if (detailId) return <PayrollDetailScreen employeeId={detailId} date={date} onBack={() => setDetailId(null)} />; if (result) return <PayrollResultScreen result={result} rows={rows} onBack={() => setResult(null)} />;
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
      {approvableIds.length > 0 && (
        <label className="select-all-row">
          <input type="checkbox" checked={allSelected} onChange={toggleAll} />
          <span>Chọn tất cả dòng đủ điều kiện duyệt ({approvableIds.length})</span>
        </label>
      )}
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
      <span className="date-nav__label">{new Intl.DateTimeFormat("vi-VN", {timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric"}).format(new Date(`${value}T12:00:00+07:00`))}</span>
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
          <Button tone="danger" busy={busy} disabled={!rows.length} onClick={onApprove}>Xác nhận duyệt</Button>
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
