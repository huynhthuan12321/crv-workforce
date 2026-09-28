import {useCallback, useEffect, useState} from "react";
import {ApiError, api} from "../../../api/client";
import {Button, Card, Chip, Metric, ScreenState, SectionTitle} from "../../../components/ui";
import {fmtDate, todayVN} from "../../../lib/date-vn";
import {fmtMoney} from "../../../lib/format";
import {hapticNotify} from "../../../lib/haptic";
import {getCurrentLocation} from "../../../lib/location";
import type {ManagedEmployee, RateHistory, WorkLocation} from "../../../types/api";
import {errorText, useBackButton} from "../shared";

const USE_MOCK = import.meta.env.DEV && import.meta.env.VITE_MOCK === "1";

function mockScenario() {
  if (!USE_MOCK) return "";
  return new URLSearchParams(window.location.search).get("scenario") ?? "";
}

function mockKey(...parts: string[]) {
  return parts.join("_");
}

export function EmployeesScreen() {
  const scenario = mockScenario();
  const [rows, setRows] = useState<ManagedEmployee[]>([]);
  const [q, setQ] = useState("");
  const [active, setActive] = useState<"all" | "active" | "locked">("all");
  const [subtab, setSubtab] = useState<"employees" | "locations">("employees");
  const [screen, setScreen] = useState<"list" | "add" | "detail">(scenario === mockKey("manager", "employee", "add") ? "add" : scenario === mockKey("manager", "employee", "detail") ? "detail" : "list");
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
  if (subtab === "locations") return <LocationsScreen onBack={() => setSubtab("employees")} canAssignEmployees />;
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
      <div className="segmented">
        <button className={(subtab as string) === "employees" ? "active" : ""} onClick={() => setSubtab("employees")}>Nhân viên</button>
        <button className={(subtab as string) === "locations" ? "active" : ""} onClick={() => setSubtab("locations")}>Kho</button>
      </div>
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
              {row.work_location && <small>Kho: {row.work_location.code} · {row.work_location.name}</small>}
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

type GpsCapture = {lat: number; lng: number; accuracy_m: number | null} | null;

function accuracyText(gps: GpsCapture) {
  if (!gps) return null;
  if (gps.accuracy_m == null) return {tone: "danger" as const, text: "⚠ Không xác định được độ chính xác"};
  const m = Math.round(gps.accuracy_m);
  if (gps.accuracy_m <= 30) return {tone: "success" as const, text: `● Tốt · ±${m} m`};
  if (gps.accuracy_m <= 100) return {tone: "warning" as const, text: `⚠ Trung bình · ±${m} m · nên kiểm tra trên bản đồ trước khi lưu`};
  return {tone: "danger" as const, text: `⚠ Thấp · ±${m} m`};
}

export function LocationsScreen({onBack, canAssignEmployees = true}: {onBack: () => void; canAssignEmployees?: boolean}) {
  const [rows, setRows] = useState<WorkLocation[]>([]);
  const [form, setForm] = useState({code: "", name: "", latitude: "", longitude: "", radius_m: 100});
  const [editing, setEditing] = useState<WorkLocation | null>(null);
  const [gps, setGps] = useState<GpsCapture>(null);
  const [needConfirm, setNeedConfirm] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const canSaveLocation = form.code.trim().length > 0 && form.name.trim().length > 0;

  const load = useCallback(async () => {
    try {
      setRows(await api.get<WorkLocation[]>("/locations"));
    } catch (err) {
      setError(errorText(err));
    }
  }, []);

  useEffect(() => void load(), [load]);

  const captureGps = async () => {
    setBusy(true);
    setError(null);
    try {
      const location = await getCurrentLocation();
      setGps(location);
      setNeedConfirm(location.accuracy_m == null || location.accuracy_m > 100);
      setForm((current) => ({...current, latitude: String(location.lat), longitude: String(location.lng)}));
    } catch (err) {
      hapticNotify("error");
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const save = async (source: "gps" | "manual", lowAccuracyConfirmed = false) => {
    const nextErrors: Record<string, string> = {};
    if (!form.code.trim()) nextErrors.code = "Vui lòng nhập mã kho.";
    if (!form.name.trim()) nextErrors.name = "Vui lòng nhập tên kho.";
    if (Object.keys(nextErrors).length > 0) {
      setFieldErrors(nextErrors);
      return;
    }
    setBusy(true);
    setError(null);
    setFieldErrors({});
    try {
      const body = {
        code: form.code.trim().toUpperCase(),
        name: form.name.trim(),
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        radius_m: form.radius_m,
        coordinate_source: source === "gps" ? "device_gps" : "manual_coordinates",
        location_accuracy_m: source === "gps" ? gps?.accuracy_m ?? null : null,
        low_accuracy_confirmed: source !== "gps" || !gps || (gps.accuracy_m != null && gps.accuracy_m <= 100) || lowAccuracyConfirmed,
      };
      if (editing) await api.patch<WorkLocation>(`/locations/${editing.id}`, body);
      else await api.post<WorkLocation>("/locations", body);
      setForm({code: "", name: "", latitude: "", longitude: "", radius_m: 100});
      setEditing(null);
      setGps(null);
      setNeedConfirm(false);
      hapticNotify("success");
      await load();
    } catch (err) {
      hapticNotify("error");
      if (err instanceof ApiError && err.details && typeof err.details === "object" && "fields" in err.details) {
        const fields = (err.details as {fields?: Record<string, string>}).fields;
        if (fields) setFieldErrors(fields);
      }
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (row: WorkLocation) => {
    try {
      await api.post<WorkLocation>(`/locations/${row.id}/${row.is_active ? "deactivate" : "activate"}`);
      await load();
    } catch (err) {
      setError(errorText(err));
    }
  };

  return <div className="screen-stack">
    <Button tone="ghost" className="back-button" onClick={onBack}>← Quay lại</Button>
    <SectionTitle eyebrow="Kho" title="Quản lý điểm làm việc" />
    <Card>
      <label className="form-field">Mã kho<input className={fieldErrors.code ? "input-error" : ""} value={form.code} onChange={(event) => setForm({...form, code: event.target.value.toUpperCase()})} placeholder="VD: KHO02" />{fieldErrors.code && <small className="field-error">{fieldErrors.code}</small>}</label>
      <label className="form-field">Tên kho<input className={fieldErrors.name ? "input-error" : ""} value={form.name} onChange={(event) => setForm({...form, name: event.target.value})} placeholder="Kho đóng gói" />{fieldErrors.name && <small className="field-error">{fieldErrors.name}</small>}</label>
      <div className="two-col">
        <label className="form-field">Vĩ độ<input value={form.latitude} onChange={(event) => setForm({...form, latitude: event.target.value})} /></label>
      <label className="form-field">Kinh độ<input value={form.longitude} onChange={(event) => setForm({...form, longitude: event.target.value})} /></label>
      </div>
      <label className="form-field">Bán kính (m)<input type="number" value={form.radius_m} onChange={(event) => setForm({...form, radius_m: Number(event.target.value)})} /></label>
      {gps && <div className="chip-row"><Chip tone={accuracyText(gps)?.tone ?? "neutral"}>{accuracyText(gps)?.text}</Chip></div>}
      {needConfirm && <p className="muted">Độ chính xác ước tính thấp. Hãy thử lấy lại vị trí; nếu vẫn cần lưu, bấm “Vẫn lưu vị trí này”.</p>}
      {error && <p className="form-error">{error}</p>}
      <div className="action-row">
        <Button tone="secondary" busy={busy} onClick={() => void captureGps()}>Thử lấy vị trí GPS</Button>
        {needConfirm
          ? <Button tone="warning" busy={busy} onClick={() => void save("gps", true)}>Vẫn lưu vị trí này</Button>
          : <Button busy={busy} disabled={!canSaveLocation} onClick={() => void save(gps ? "gps" : "manual")}>{editing ? "Lưu kho" : "Tạo kho"}</Button>}
      </div>
    </Card>
    {rows.map((row) => <Card key={row.id} className="manager-card">
      <div className="manager-row">
        <div>
          <b>{row.code} · {row.name}</b>
          <small>{row.latitude.toFixed(6)}, {row.longitude.toFixed(6)} · bán kính {row.radius_m} m</small>
        </div>
        <Chip tone={row.is_active ? "success" : "danger"}>{row.is_active ? "Đang dùng" : "Ngừng dùng"}</Chip>
      </div>
      <div className="action-row">
        <Button tone="secondary" onClick={() => {
          setEditing(row);
          setForm({code: row.code, name: row.name, latitude: String(row.latitude), longitude: String(row.longitude), radius_m: row.radius_m});
          setGps(row.coordinate_source === "device_gps" && row.location_accuracy_m != null ? {lat: row.latitude, lng: row.longitude, accuracy_m: row.location_accuracy_m} : null);
          setNeedConfirm(false);
        }}>Sửa</Button>
        <Button tone="secondary" onClick={() => void toggle(row)}>{row.is_active ? "Ngừng dùng" : "Dùng lại"}</Button>
      </div>
      {!canAssignEmployees && <p className="muted">Giám đốc chỉ quản lý danh mục kho, không phân công nhân viên tại đây.</p>}
    </Card>)}
  </div>;
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
