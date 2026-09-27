import {useCallback, useEffect, useState} from "react";
import {api} from "../../../api/client";
import {Card, Chip, ScreenState, SectionTitle} from "../../../components/ui";
import {fmtDuration, fmtTime} from "../../../lib/date-vn";
import type {WorkingNowItem} from "../../../types/api";
import {errorText} from "../shared";

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

