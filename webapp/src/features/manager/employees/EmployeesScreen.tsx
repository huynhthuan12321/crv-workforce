import {useCallback, useEffect, useState} from "react";
import {api} from "../../../api/client";
import {Button, Card, Chip, Metric, ScreenState, SectionTitle} from "../../../components/ui";
import {fmtDate, todayVN} from "../../../lib/date-vn";
import {fmtMoney} from "../../../lib/format";
import {hapticNotify} from "../../../lib/haptic";
import type {ManagedEmployee, RateHistory} from "../../../types/api";
import {errorText, useBackButton} from "../shared";

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
        <label className="form-field">Hiệu lực từ ngày<input type="date" min={todayVN()} value={form.effective_from} onChange={(event) => setField("effective_from", event.target.value)} /><small className="date-label">{new Intl.DateTimeFormat("vi-VN", {timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric"}).format(new Date(`${form.effective_from}T12:00:00+07:00`))}</small></label>
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
          <label className="form-field">Hiệu lực từ ngày<input type="date" min={todayVN()} value={rate.effective_from} onChange={(event) => setRate({...rate, effective_from: event.target.value})} /><small className="date-label">{new Intl.DateTimeFormat("vi-VN", {timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric"}).format(new Date(`${rate.effective_from}T12:00:00+07:00`))}</small></label>
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
