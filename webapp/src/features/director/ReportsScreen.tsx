import {useCallback, useEffect, useMemo, useState} from "react";
import {api} from "../../api/client";
import {Button, Card, Metric, ScreenState, SectionTitle, SearchInput} from "../../components/ui";
import {fmtMoney} from "../../lib/format";
import {periodBounds, periodLabel, shiftPeriod, type ReportPeriod} from "../../lib/report-period";
import {fmtHours, fmtKg} from "../../lib/report-format";
import {hapticImpact} from "../../lib/haptic";
import {todayVN} from "../../lib/date-vn";
import type {ProductTotal, ReportEmployee, ReportSummary, ReportTimeseries} from "../../types/api";
import {useBackButton} from "../manager/shared";

function reportMockScenario() {
  if (!(import.meta.env.DEV && import.meta.env.VITE_MOCK === "1")) return "";
  return new URLSearchParams(window.location.search).get("scenario") ?? "";
}

function reportToday() {
  if (!(import.meta.env.DEV && import.meta.env.VITE_MOCK === "1")) return todayVN();
  return "2026-09-27";
}

function mockKey(...parts: string[]) {
  return parts.join("_");
}

function ReportChart({rows}: {rows: ReportTimeseries[]}) {
  if (rows.length <= 1) return <p className="muted">Chọn Tuần hoặc Tháng để xem biểu đồ</p>;
  const maxMinutes = Math.max(...rows.map((row) => row.minutes), 1);
  const maxSalary = Math.max(...rows.map((row) => row.salary), 1);
  const width = 360, height = 170, left = 32, bottom = 28, top = 12, plotW = width - left - 10, plotH = height - bottom - top;
  const points = rows.map((row, index) => {
    const x = left + (index * plotW) / Math.max(rows.length - 1, 1);
    return {x, y: top + plotH - (row.salary / maxSalary) * plotH, row};
  });
  return <div className="report-chart"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Biểu đồ giờ công và lương">
    <line x1={left} y1={top} x2={left} y2={top + plotH} stroke="var(--crv-border)" />
    <line x1={width - 10} y1={top} x2={width - 10} y2={top + plotH} stroke="var(--crv-border)" />
    <line x1={left} y1={top + plotH} x2={width - 10} y2={top + plotH} stroke="var(--crv-border)" />
    <text x={left - 24} y={top + 8} className="chart-axis-label">Giờ</text>
    <text x={width - 10} y={top + 8} textAnchor="end" className="chart-axis-label">Lương</text>
    {rows.map((row, index) => {
      const barW = Math.max(12, plotW / rows.length - 8);
      const x = left + (index * plotW) / Math.max(rows.length - 1, 1) - barW / 2;
      const h = (row.minutes / maxMinutes) * plotH;
      const visibleHeight = h || 8;
      return <rect key={row.date} x={x} y={top + plotH - visibleHeight} width={barW} height={visibleHeight} rx="4" fill={h ? "var(--crv-primary-soft)" : "transparent"} stroke={h ? "none" : "var(--crv-border)"} aria-label={`${row.date}: ${fmtHours(row.minutes)}, ${fmtMoney(row.salary)}`} onClick={() => window.alert(`${row.date}: ${fmtHours(row.minutes)}, ${fmtMoney(row.salary)}`)} />;
    })}
    <polyline points={points.map((point) => `${point.x},${point.y}`).join(" ")} fill="none" stroke="var(--crv-warning)" strokeWidth="3" />
    {points.map((point) => <circle key={point.row.date} cx={point.x} cy={point.y} r="3.5" fill="var(--crv-warning)" />)}
  </svg><div className="chart-legend"><span>■ Giờ công</span><span>━ Lương</span></div></div>;
}

function EmployeePicker({selected, onSelect, onClose}: {selected: ReportEmployee | null; onSelect: (employee: ReportEmployee | null) => void; onClose: () => void}) {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<ReportEmployee[]>([]);
  useEffect(() => { void api.get<ReportEmployee[]>(`/reports/employees${query ? `?q=${encodeURIComponent(query)}` : ""}`).then(setRows); }, [query]);
  return <div className="screen-stack"><Button tone="ghost" className="back-button" onClick={onClose}>← Quay lại</Button><Card>
    <SectionTitle eyebrow="Bộ lọc" title="Chọn nhân viên" />
    <SearchInput placeholder="Tìm tên hoặc mã" value={query} onChange={(event) => setQuery(event.target.value)} />
    <button className={`picker-row ${!selected ? "active" : ""}`} onClick={() => { onSelect(null); onClose(); }}>Tất cả nhân viên</button>
    {rows.map((row) => <button key={row.id} className={`picker-row ${selected?.id === row.id ? "active" : ""}`} onClick={() => { onSelect(row); onClose(); }}>{row.code} · {row.full_name}</button>)}
  </Card></div>;
}

export function ReportsScreen() {
  const scenario = reportMockScenario();
  const initialPeriod: ReportPeriod = scenario === mockKey("director", "report", "day") ? "day" : scenario === mockKey("director", "report", "month") ? "month" : "week";
  const today = reportToday();
  const [period, setPeriod] = useState<ReportPeriod>(initialPeriod);
  const [date, setDate] = useState(today);
  const [employee, setEmployee] = useState<ReportEmployee | null>(null);
  const [picker, setPicker] = useState(scenario === mockKey("director", "report", "employees"));
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [series, setSeries] = useState<ReportTimeseries[]>([]);
  const [products, setProducts] = useState<ProductTotal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const query = `period=${period}&date=${date}${employee ? `&employee_id=${employee.id}` : ""}`;
      const [nextSummary, nextSeries, nextProducts] = await Promise.all([
        api.get<ReportSummary>(`/reports/summary?${query}`),
        api.get<ReportTimeseries[]>(`/reports/timeseries?${query}`),
        api.get<ProductTotal[]>(`/reports/products?${query}`),
      ]);
      setSummary(nextSummary); setSeries(nextSeries); setProducts(nextProducts);
    } catch (err) { setError(err instanceof Error ? err.message : "Không tải được báo cáo"); }
    finally { setLoading(false); }
  }, [date, employee, period]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (scenario !== mockKey("director", "report", "filtered")) return;
    void api.get<ReportEmployee[]>("/reports/employees").then((rows) => setEmployee(rows[0] ?? null));
  }, [scenario]);
  useBackButton(picker, () => setPicker(false));
  if (picker) return <EmployeePicker selected={employee} onSelect={setEmployee} onClose={() => setPicker(false)} />;
  if (loading) return <ScreenState kind="loading" title="Đang tải báo cáo" />;
  if (error) return <ScreenState kind="error" title="Không tải được báo cáo" message={error} onRetry={load} />;
  if (!summary) return <ScreenState kind="empty" title="Không có dữ liệu" />;
  const total = products.reduce((acc, row) => ({bags: acc.bags + row.bags, kg: acc.kg + row.kg}), {bags: 0, kg: 0});
  const bounds = periodBounds(period, date);
  const canNext = bounds.to < today;
  return <div className="screen-stack reports-screen">
    <SectionTitle eyebrow="Báo cáo" title="Tổng quan" />
    <div className="segmented">{(["day", "week", "month"] as const).map((key) => <button key={key} className={period === key ? "active" : ""} onClick={() => { hapticImpact(); setPeriod(key); }}>{key === "day" ? "Ngày" : key === "week" ? "Tuần" : "Tháng"}</button>)}</div>
    <div className="report-period-nav"><button onClick={() => setDate(shiftPeriod(period, date, -1))}>‹</button><b>{periodLabel(period, date)}</b><button disabled={!canNext} onClick={() => setDate(shiftPeriod(period, date, 1))}>›</button></div>
    <button className="filter-chip" onClick={() => setPicker(true)}>{employee ? `${employee.code} · ${employee.full_name} ✕` : "Tất cả nhân viên"}</button>
    <div className="mini-grid"><Metric label="Giờ công" value={fmtHours(summary.minutes)} /><Metric label="Tổng túi" value={summary.bags.toLocaleString("vi-VN")} /><Metric label="Tổng kg" value={fmtKg(summary.kg)} /></div>
    <Card>
      <SectionTitle title="Lương" />
      <div className="salary-total"><Metric label="Tổng" value={fmtMoney(summary.total)} /></div>
      <div className="mini-grid mini-grid--three">
        <Metric label="Đã trả" value={fmtMoney(summary.paid)} tone="success" />
        <Metric label="Chờ duyệt" value={fmtMoney(summary.pending_eligible)} tone="warning" />
        <Metric label="Cần xử lý" value={fmtMoney(summary.pending_blocked)} tone="info" />
      </div>
      {summary.needs_review_count > 0 && <p className="muted">{summary.needs_review_count} phiên quên ra ca chưa có giờ ra.</p>}
    </Card>
    <Card><SectionTitle title="Biểu đồ theo ngày" /><ReportChart rows={series} /></Card>
    <Card><SectionTitle title="Sản lượng theo mặt hàng" /><div className="product-table"><div className="product-table__head"><span>Mặt hàng</span><span>Túi</span><span>Kg</span></div>{products.map((row) => <div className="product-table__row" key={row.code}><span>{row.name}</span><span>{row.bags}</span><span>{row.kg.toLocaleString("vi-VN", {minimumFractionDigits: 1})}</span></div>)}<div className="product-table__row product-table__total"><b>Tổng</b><b>{total.bags}</b><b>{total.kg.toLocaleString("vi-VN", {minimumFractionDigits: 1})}</b></div></div></Card>
  </div>;
}
