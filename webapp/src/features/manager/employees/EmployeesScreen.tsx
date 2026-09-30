import {useCallback, useEffect, useState} from "react";
import {ApiError, api} from "../../../api/client";
import {Button, Card, Chip, Metric, ScreenState, SectionTitle} from "../../../components/ui";
import {fmtDate, fmtTime, todayVN} from "../../../lib/date-vn";
import {fmtKg, fmtMoney} from "../../../lib/format";
import {hapticNotify} from "../../../lib/haptic";
import {getCurrentLocation} from "../../../lib/location";
import type {CatalogProduct, EmployeeLocationHistory, ManagedEmployee, RateHistory, WorkLocation} from "../../../types/api";
import {errorText, useBackButton} from "../shared";

const USE_MOCK = import.meta.env.DEV && import.meta.env.VITE_MOCK === "1";

function mockScenario() {
  if (!USE_MOCK) return "";
  return new URLSearchParams(window.location.search).get("scenario") ?? "";
}

function mockKey(...parts: string[]) {
  return parts.join("_");
}

function fmtDateTime(value?: string | null) {
  if (!value) return "đến nay";
  return `${fmtDate(value, {day: "2-digit", month: "2-digit", year: "numeric"})} ${fmtTime(value)}`;
}

function displayLocationReason(reason?: string | null) {
  if (!reason) return null;
  return reason.trim().toLowerCase() === "backfill kho01" ? "Kho ban đầu" : reason;
}

type LocationUseDetails = {current_assignments?: unknown; open_sessions?: unknown};

function detailCount(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (Array.isArray(value)) return value.length;
  return 0;
}

const MIN_HOURLY_RATE = 1_000;
const MAX_HOURLY_RATE = 1_000_000;

function isRateOutOfRange(rate: Pick<RateHistory, "hourly_rate"> & {is_out_of_range?: boolean}) {
  return Boolean(rate.is_out_of_range)
    || rate.hourly_rate < MIN_HOURLY_RATE
    || rate.hourly_rate > MAX_HOURLY_RATE;
}

export function pendingRatesForDisplay(employee: ManagedEmployee): RateHistory[] {
  if (employee.pending_rates?.length) return employee.pending_rates as RateHistory[];
  return employee.pending_rate ? [employee.pending_rate as RateHistory] : [];
}

export function formatLocationInUseMessage(locationName: string, details?: LocationUseDetails | null) {
  const assignments = detailCount(details?.current_assignments);
  const openSessions = detailCount(details?.open_sessions);
  const parts = [`còn ${assignments} nhân viên đang phân công`];
  if (openSessions > 0) parts.push(`${openSessions} ca đang mở`);
  return `Không thể ngừng dùng ${locationName}: ${parts.join(", ")}. Chuyển nhân viên sang kho khác trước.`;
}

export function EmployeesScreen() {
  const scenario = mockScenario();
  const [rows, setRows] = useState<ManagedEmployee[]>([]);
  const [q, setQ] = useState("");
  const [active, setActive] = useState<"all" | "active" | "locked">("all");
  const [locationFilter, setLocationFilter] = useState<number | "all">("all");
  const [locations, setLocations] = useState<WorkLocation[]>([]);
  const [subtab, setSubtab] = useState<"employees" | "locations" | "products">(scenario.startsWith(mockKey("manager", "locations")) ? "locations" : "employees");
  const [screen, setScreen] = useState<"list" | "add" | "detail">(scenario === mockKey("manager", "employee", "add") ? "add" : scenario.startsWith(mockKey("manager", "employee", "assign")) || scenario === mockKey("manager", "employee", "detail") ? "detail" : "list");
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
      const [data, locationRows] = await Promise.all([
        api.get<ManagedEmployee[]>(`/employees${params.toString() ? `?${params}` : ""}`),
        api.get<WorkLocation[]>("/locations?active=true"),
      ]);
      setRows(data);
      setLocations(locationRows);
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
  if (subtab === "products") return <ProductCatalogScreen onBack={() => setSubtab("employees")} />;
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

  const visibleRows = rows.filter((row) => locationFilter === "all" || (row.current_location?.id ?? row.work_location?.id) === locationFilter);

  return (
    <div className="screen-stack">
      <SectionTitle eyebrow="Nhân viên" title="Danh sách nhân viên" action={<Button className="small-button" onClick={() => setScreen("add")}>Thêm</Button>} />
      <div className="segmented">
        <button className={(subtab as string) === "employees" ? "active" : ""} onClick={() => setSubtab("employees")}>Nhân viên</button>
        <button className={(subtab as string) === "locations" ? "active" : ""} onClick={() => setSubtab("locations")}>Kho</button>
        <button className={(subtab as string) === "products" ? "active" : ""} onClick={() => setSubtab("products")}>Sản phẩm</button>
      </div>
      <Card>
        <label className="form-field">Tìm kiếm<input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Tên hoặc mã nhân viên" /></label>
        <div className="segmented">
          <button className={active === "all" ? "active" : ""} onClick={() => setActive("all")}>Tất cả</button>
          <button className={active === "active" ? "active" : ""} onClick={() => setActive("active")}>Đang hoạt động</button>
          <button className={active === "locked" ? "active" : ""} onClick={() => setActive("locked")}>Đã khóa</button>
        </div>
        <div className="location-chip-row">
          <Button className="small-button" tone={locationFilter === "all" ? "primary" : "secondary"} onClick={() => setLocationFilter("all")}>Tất cả kho</Button>
          {locations.map((location) => (
            <Button key={location.id} className="small-button" tone={locationFilter === location.id ? "primary" : "secondary"} onClick={() => setLocationFilter(location.id)}>{location.code}</Button>
          ))}
        </div>
      </Card>
      {visibleRows.map((row) => (
        <Card key={row.id} className="manager-card">
          <div className="manager-row">
            <button className="plain-button" onClick={() => { setSelected(row); setScreen("detail"); }}>
              <b>{row.full_name}</b>
              <small>{row.code} · {fmtMoney(row.current_hourly_rate ?? 0)}/giờ</small>
              {(row.current_location || row.work_location) && <small>Kho: {row.current_location?.code ?? row.work_location?.code} · {row.current_location?.name ?? row.work_location?.name}</small>}
            </button>
            <button type="button" className={`switch ${row.is_active ? "on" : ""}`} aria-label={row.is_active ? "Khóa" : "Mở khóa"} onClick={() => void toggleLock(row)} />
          </div>
          <div className="chip-row">
            {!row.is_linked && <Chip tone="warning">Chưa liên kết</Chip>}
            {row.has_open_session && <Chip tone="info">Đang trong ca</Chip>}
            {!row.is_active && <Chip tone="danger">Đã khóa</Chip>}
            {(row.current_location || row.work_location) && <Chip tone="neutral">{row.current_location?.code ?? row.work_location?.code}</Chip>}
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
  const [locationErrors, setLocationErrors] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);
  const [expandedLocation, setExpandedLocation] = useState<number | null>(null);
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
      setLocationErrors((current) => ({...current, [row.id]: ""}));
      await api.post<WorkLocation>(`/locations/${row.id}/${row.is_active ? "deactivate" : "activate"}`);
      await load();
    } catch (err) {
      hapticNotify("error");
      if (err instanceof ApiError && err.code === "LOCATION_IN_USE") {
        setLocationErrors((current) => ({
          ...current,
          [row.id]: formatLocationInUseMessage(row.name, err.details as LocationUseDetails | undefined),
        }));
        return;
      }
      setLocationErrors((current) => ({...current, [row.id]: errorText(err)}));
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
          <small>{row.current_employee_count ?? 0} nhân viên đang phân công</small>
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
        <Button tone="secondary" onClick={() => setExpandedLocation(expandedLocation === row.id ? null : row.id)}>Danh sách nhân viên</Button>
      </div>
      {locationErrors[row.id] && (
        <div className="form-error">
          <p>{locationErrors[row.id]}</p>
          <Button tone="secondary" className="small-button" onClick={() => setExpandedLocation(row.id)}>Xem nhân viên</Button>
        </div>
      )}
      {expandedLocation === row.id && (
        <div className="history-block">
          {(row.current_employees ?? []).length === 0
            ? <p className="muted">Chưa có nhân viên đang phân công.</p>
            : (row.current_employees ?? []).map((employee) => <div className="session-row" key={employee.id}><span>{employee.full_name}</span><small>{employee.code}</small></div>)}
        </div>
      )}
      {!canAssignEmployees && <p className="muted">Giám đốc chỉ quản lý danh mục kho, không phân công nhân viên tại đây.</p>}
    </Card>)}
  </div>;
}

export function ProductCatalogScreen({onBack}: {onBack: () => void}) {
  const [rows, setRows] = useState<CatalogProduct[]>([]);
  const [form, setForm] = useState({code: "", name: "", kg_per_unit: "1", unit_label: "Túi", scope: "all"});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setRows(await api.get<CatalogProduct[]>("/catalog/products"));
    } catch (err) {
      setError(errorText(err));
    }
  }, []);

  useEffect(() => void load(), [load]);

  const create = async () => {
    if (!form.code.trim() || !form.name.trim()) {
      setError("Vui lòng nhập mã và tên sản phẩm.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.post<CatalogProduct>("/catalog/products", {
        code: form.code.trim().toUpperCase(),
        name: form.name.trim(),
        kg_per_unit: Number(form.kg_per_unit),
        unit_label: form.unit_label.trim() || "Túi",
        unit_code: "BAG",
        scope: form.scope,
        location_ids: [],
        employee_ids: [],
      });
      setForm({code: "", name: "", kg_per_unit: "1", unit_label: "Túi", scope: "all"});
      hapticNotify("success");
      await load();
    } catch (err) {
      hapticNotify("error");
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const toggleActive = async (product: CatalogProduct) => {
    try {
      await api.post<CatalogProduct>(`/catalog/products/${product.id}/${product.is_active ? "deactivate" : "reactivate"}`);
      await load();
    } catch (err) {
      setError(errorText(err));
    }
  };

  const remove = async (product: CatalogProduct) => {
    if (!window.confirm(`Xóa sản phẩm ${product.name}? Chỉ dùng cho sản phẩm tạo nhầm chưa từng xuất hiện trong sản lượng.`)) return;
    try {
      await api.delete<CatalogProduct>(`/catalog/products/${product.id}`);
      await load();
    } catch (err) {
      setError(errorText(err));
    }
  };

  const scopeLabel = (product: CatalogProduct) => {
    if (product.scope === "all") return "Chung";
    const {location_count, employee_count, applied_employee_count} = product.scope_summary;
    if (applied_employee_count === 0) return "Chưa áp dụng cho ai";
    return `${location_count} kho · ${employee_count} nhân viên`;
  };

  return (
    <div className="screen-stack">
      <Button tone="ghost" className="back-button" onClick={onBack}>← Quay lại</Button>
      <SectionTitle eyebrow="Sản phẩm" title="Danh mục sản phẩm" />
      <Card>
        <SectionTitle title="Thêm sản phẩm" />
        <label className="form-field">Mã sản phẩm<input value={form.code} onChange={(event) => setForm({...form, code: event.target.value.toUpperCase()})} placeholder="VD: BOT" /></label>
        <label className="form-field">Tên sản phẩm<input value={form.name} onChange={(event) => setForm({...form, name: event.target.value})} placeholder="Bột" /></label>
        <div className="two-col">
          <label className="form-field">Kg/đơn vị<input type="number" min="0.001" step="0.001" value={form.kg_per_unit} onChange={(event) => setForm({...form, kg_per_unit: event.target.value})} /></label>
          <label className="form-field">Đơn vị<input value={form.unit_label} onChange={(event) => setForm({...form, unit_label: event.target.value})} /></label>
        </div>
        <label className="form-field">Áp dụng cho<select value={form.scope} onChange={(event) => setForm({...form, scope: event.target.value})}><option value="all">Tất cả nhân viên</option><option value="restricted">Chỉ kho và nhân viên được chọn</option></select></label>
        {form.scope === "restricted" && <p className="muted">Sản phẩm chưa áp dụng cho ai. Bạn có thể lưu trước rồi chỉnh phạm vi chi tiết ở bản hoàn thiện.</p>}
        {error && <p className="form-error">{error}</p>}
        <Button busy={busy} disabled={!form.code.trim() || !form.name.trim()} onClick={create}>Tạo sản phẩm</Button>
      </Card>
      {rows.map((product) => (
        <Card key={product.id} className="manager-card">
          <div className="manager-row">
            <div>
              <b>{product.code} · {product.name}</b>
              <small>{fmtKg(product.kg_per_unit)}/{product.unit_label}</small>
            </div>
            <Chip tone={product.is_active ? "success" : "danger"}>{product.is_active ? "Đang sản xuất" : "Ngừng SX"}</Chip>
          </div>
          <div className="chip-row">
            <Chip tone={product.scope_summary.applied_employee_count === 0 && product.scope !== "all" ? "warning" : "neutral"}>{scopeLabel(product)}</Chip>
            {product.used && <Chip tone="info">Đã có dữ liệu</Chip>}
          </div>
          <div className="action-row">
            <Button tone="secondary" onClick={() => void toggleActive(product)}>{product.is_active ? "Ngừng" : "Kích hoạt"}</Button>
            {!product.used && <Button tone="danger" onClick={() => void remove(product)}>Xóa tạo nhầm</Button>}
          </div>
        </Card>
      ))}
    </div>
  );
}

function EmployeeAddScreen({onBack, onCreated, invite}: {onBack: () => void; onCreated: (url: string) => void; invite: string | null}) {
  const [form, setForm] = useState({code: "", full_name: "", hourly_rate: 30000, effective_from: todayVN(), location_id: ""});
  const [locations, setLocations] = useState<WorkLocation[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setField = (key: keyof typeof form, value: string | number) => setForm((current) => ({...current, [key]: value}));
  useEffect(() => {
    void api.get<WorkLocation[]>("/locations?active=true").then(setLocations).catch((err) => setError(errorText(err)));
  }, []);
  const submit = async () => {
    if (!form.location_id) {
      setError("Vui lòng chọn kho chấm công.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await api.post<ManagedEmployee>("/employees", {...form, location_id: Number(form.location_id)});
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
        <label className="form-field">Kho chấm công<select value={form.location_id} onChange={(event) => setField("location_id", event.target.value)}><option value="">Chọn kho</option>{locations.map((location) => <option key={location.id} value={location.id}>{location.code} · {location.name}</option>)}</select></label>
        <label className="form-field">Hiệu lực từ ngày<input type="date" min={todayVN()} value={form.effective_from} onChange={(event) => setField("effective_from", event.target.value)} /><small className="date-label">{new Intl.DateTimeFormat("vi-VN", {timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric"}).format(new Date(`${form.effective_from}T12:00:00+07:00`))}</small></label>
        {error && <p className="form-error">{error}</p>}
        <Button busy={busy} disabled={!form.location_id} onClick={submit}>Tạo nhân viên</Button>
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

export function EmployeeDetailScreen({employee, onBack, onChanged}: {employee: ManagedEmployee | null; onBack: () => void; onChanged: () => void}) {
  const scenario = mockScenario();
  const [rates, setRates] = useState<RateHistory[]>([]);
  const [rate, setRate] = useState({hourly_rate: 32000, mode: "next_shift", effective_date: todayVN(), reason: "Tăng theo năng lực", confirm_large_change: false});
  const [detail, setDetail] = useState<ManagedEmployee | null>(employee);
  const [locations, setLocations] = useState<WorkLocation[]>([]);
  const [history, setHistory] = useState<EmployeeLocationHistory[]>([]);
  const [showHistory, setShowHistory] = useState(true);
  const [assigning, setAssigning] = useState(scenario.startsWith(mockKey("manager", "employee", "assign")));
  const [assignment, setAssignment] = useState({location_id: "", reason: ""});
  const [invite, setInvite] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmRate, setConfirmRate] = useState("");

  const load = useCallback(async () => {
    if (!employee) return;
    try {
      const [detailRow, rateRows, locationRows, historyRows] = await Promise.all([
        api.get<ManagedEmployee>(`/employees/${employee.id}`),
        api.get<RateHistory[]>(`/employees/${employee.id}/rates`),
        api.get<WorkLocation[]>("/locations?active=true"),
        api.get<EmployeeLocationHistory[]>(`/employees/${employee.id}/location-history`),
      ]);
      setDetail(detailRow);
      setRates(rateRows);
      setLocations(locationRows);
      setHistory(historyRows);
    } catch (err) {
      setError(errorText(err));
    }
  }, [employee]);

  useEffect(() => void load(), [load]);

  if (!employee || !detail) return <ScreenState kind="empty" title="Chưa chọn nhân viên" />;

  const currentLocation = detail.current_location ?? (detail.work_location ? {id: detail.work_location.id, code: detail.work_location.code, name: detail.work_location.name, effective_from: undefined} : null);
  const otherLocations = locations.filter((location) => location.id !== currentLocation?.id);
  const pendingRates = pendingRatesForDisplay(detail);

  const saveRate = async () => {
    setBusy(true);
    setConfirmRate("");
    try {
      const payload = {
        hourly_rate: rate.hourly_rate,
        mode: rate.mode,
        effective_date: rate.mode === "date" ? rate.effective_date : undefined,
        reason: rate.reason.trim(),
        confirm_large_change: rate.confirm_large_change,
      };
      const data = await api.post<{requires_confirmation?: boolean; message?: string} | RateHistory>(`/employees/${detail.id}/rates`, payload);
      if ("requires_confirmation" in data && data.requires_confirmation) {
        setConfirmRate(data.message || "Thay đổi lớn, vui lòng xác nhận lần nữa.");
        setRate({...rate, confirm_large_change: true});
        return;
      }
      hapticNotify("success");
      setRate({...rate, confirm_large_change: false});
      await load();
      onChanged();
    } catch (err) {
      hapticNotify("error");
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const cancelRate = async (item: RateHistory) => {
    const reason = window.prompt("Nhập lý do hủy mức hẹn", "Hủy theo yêu cầu");
    if (!reason || reason.trim().length < 5) return;
    setBusy(true);
    try {
      await api.post(`/employees/${detail.id}/rates/${item.id}/cancel`, {reason});
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
    const data = await api.post<ManagedEmployee>(`/employees/${detail.id}/invite`);
    setInvite(data.invite_url || null);
  };

  const assignLocation = async () => {
    if (!assignment.location_id || assignment.reason.trim().length < 5) {
      setError("Vui lòng chọn kho và nhập lý do từ 5 ký tự.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await api.post<ManagedEmployee>(`/locations/employees/${detail.id}/assignment`, {
        location_id: Number(assignment.location_id),
        reason: assignment.reason.trim(),
      });
      setDetail(updated);
      setAssigning(false);
      setAssignment({location_id: "", reason: ""});
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

  if (assigning) {
    return (
      <div className="screen-stack">
        <Button tone="ghost" className="back-button" onClick={() => setAssigning(false)}>← Quay lại</Button>
        <Card>
          <SectionTitle eyebrow={detail.code} title="Đổi kho chấm công" />
          <p className="muted">Áp dụng từ lần vào ca tiếp theo. Ca đang mở giữ nguyên kho cũ.</p>
          {detail.has_open_session && currentLocation && <p className="form-error">Nhân viên đang trong ca tại {currentLocation.code} · {currentLocation.name}</p>}
          <label className="form-field">Kho mới<select value={assignment.location_id} onChange={(event) => setAssignment({...assignment, location_id: event.target.value})}><option value="">Chọn kho đang dùng</option>{otherLocations.map((location) => <option key={location.id} value={location.id}>{location.code} · {location.name}</option>)}</select></label>
          <label className="form-field">Lý do<textarea value={assignment.reason} maxLength={200} onChange={(event) => setAssignment({...assignment, reason: event.target.value})} placeholder="Ví dụ: Điều chuyển sang kho đóng gói" /></label>
          {error && <p className="form-error">{error}</p>}
          <Button busy={busy} disabled={!assignment.location_id || assignment.reason.trim().length < 5} onClick={assignLocation}>Xác nhận đổi kho</Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="screen-stack">
      <Button tone="ghost" className="back-button" onClick={onBack}>← Quay lại</Button>
      <Card>
        <SectionTitle eyebrow={detail.code} title={detail.full_name} />
        <div className="history-block">
          <div className="manager-row">
            <div>
              <b>Kho chấm công</b>
              {currentLocation
                ? <small>{currentLocation.code} · {currentLocation.name}{currentLocation.effective_from ? ` · từ ${fmtDateTime(currentLocation.effective_from)}` : ""}</small>
                : <small>Chưa phân công kho</small>}
            </div>
            <Button className="small-button" tone="secondary" onClick={() => setAssigning(true)}>Đổi kho</Button>
          </div>
        </div>
        <Metric label={`Đơn giá hiện tại${detail.current_rate_effective_from ? ` · Hiệu lực từ ${fmtDateTime(detail.current_rate_effective_from)}` : ""}`} value={`${fmtMoney(detail.current_hourly_rate ?? 0)}/giờ`} />
        {pendingRates.map((item) => (
          <div className="history-block history-block--pending" key={item.id}>
            <div className="manager-row">
              <div>
                <b>Mức hẹn</b>
                <small>Từ {fmtDateTime(item.effective_from)} · {fmtMoney(item.hourly_rate)}/giờ</small>
                {isRateOutOfRange(item) && <small className="form-error">Vượt giới hạn cho phép – nên hủy</small>}
                {item.reason && <small>Lý do: {item.reason}</small>}
              </div>
              <Button className="small-button" tone="secondary" busy={busy} onClick={() => void cancelRate(item)}>Hủy</Button>
            </div>
          </div>
        ))}
        <SectionTitle title="Điều chỉnh đơn giá" />
        <p className="muted">Phiên đang làm hiện tại không bị thay đổi đơn giá.</p>
        <label className="form-field">Mức mới (đ/giờ)<input type="number" value={rate.hourly_rate} onChange={(event) => setRate({...rate, hourly_rate: Number(event.target.value), confirm_large_change: false})} /></label>
        <div className="choice-row">
          <label><input type="radio" checked={rate.mode === "next_shift"} onChange={() => setRate({...rate, mode: "next_shift", confirm_large_change: false})} /> Từ lần vào ca tiếp theo</label>
          <label><input type="radio" checked={rate.mode === "date"} onChange={() => setRate({...rate, mode: "date", confirm_large_change: false})} /> Từ ngày…</label>
        </div>
        {rate.mode === "date" && <label className="form-field">Ngày hiệu lực<input type="date" min={todayVN(new Date(Date.now() + 86400000))} value={rate.effective_date} onChange={(event) => setRate({...rate, effective_date: event.target.value, confirm_large_change: false})} /><small className="date-label">Có hiệu lực với các phiên bắt đầu từ ngày {new Intl.DateTimeFormat("vi-VN", {timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric"}).format(new Date(`${rate.effective_date}T12:00:00+07:00`))}</small></label>}
        <label className="form-field">Lý do nhanh<select value={rate.reason} onChange={(event) => setRate({...rate, reason: event.target.value, confirm_large_change: false})}>{["Tăng theo năng lực", "Điều chỉnh nhiệm vụ", "Thay đổi công việc", "Điều chỉnh tạm thời", "Khác"].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label className="form-field">Lý do chi tiết<textarea maxLength={200} value={rate.reason} onChange={(event) => setRate({...rate, reason: event.target.value, confirm_large_change: false})} /></label>
        {confirmRate && <div className="confirm-box"><b>Xác nhận thay đổi lớn</b><p>{confirmRate}</p></div>}
        {error && <p className="form-error">{error}</p>}
        <Button busy={busy} disabled={rate.reason.trim().length < 5} onClick={saveRate}>{rate.confirm_large_change ? "Xác nhận điều chỉnh" : "Lưu đơn giá"}</Button>
        <div className="history-block">
          <b>Lịch sử đơn giá</b>
          {rates.map((item) => <div className="session-row" key={item.id}>
            <span>{fmtMoney(item.hourly_rate)}/giờ</span>
            <small>Từ {fmtDateTime(item.effective_from)}</small>
            {item.reason && <small>Lý do: {item.reason}</small>}
            {item.is_cancelled && <Chip tone="neutral">Đã hủy</Chip>}
            {isRateOutOfRange(item) && !item.is_cancelled && <Chip tone="warning">Vượt giới hạn</Chip>}
          </div>)}
        </div>
        <div className="history-block">
          <button className="plain-button" onClick={() => setShowHistory(!showHistory)}><b>Lịch sử kho</b><small>{showHistory ? "Thu gọn" : "Mở rộng"}</small></button>
          {showHistory && history.map((item) => (
            <div className="session-row" key={item.id}>
              <span>{item.location_code} · {item.location_name}</span>
              <small>{fmtDateTime(item.effective_from)} – {fmtDateTime(item.effective_to)}</small>
              {displayLocationReason(item.reason) && <small>Lý do: {displayLocationReason(item.reason)}</small>}
              {item.changed_by_name && <small>Người đổi: {item.changed_by_name}</small>}
            </div>
          ))}
        </div>
        {!detail.is_linked && <Button tone="secondary" onClick={() => void regenerate()}>Tạo lại link mời</Button>}
        {invite && <p className="invite-box">{invite}</p>}
      </Card>
    </div>
  );
}
