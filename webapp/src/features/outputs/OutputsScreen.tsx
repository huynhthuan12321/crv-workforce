import {useCallback, useEffect, useMemo, useState} from "react";
import {api} from "../../api/client";
import {Button, Card, Chip, ScreenState, SectionTitle} from "../../components/ui";
import {fmtCountdown, fmtTime} from "../../lib/date-vn";
import {fmtKg, totalKg} from "../../lib/format";
import {hapticImpact, hapticNotify} from "../../lib/haptic";
import {serverNow, syncServerClock} from "../../lib/server-clock";
import type {History, HistorySession, OutputForm, OutputSubmit} from "../../types/api";

function eligibleSessions(history: History): HistorySession[] {
  return history.days.flatMap((day) => [
    ...day.unpaid_sessions,
    ...day.batches.flatMap((batch) => batch.sessions),
  ]).filter((session) => session.status === "closed" && Boolean(session.check_out_at));
}

export function OutputsScreen({recentSessionId}: {recentSessionId: number | null}) {
  const [history, setHistory] = useState<History>();
  const [selected, setSelected] = useState<number | null>(recentSessionId);
  const [form, setForm] = useState<OutputForm>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState(() => serverNow());

  const loadHistory = useCallback(() => api.get<History>("/history").then(setHistory).catch((e) => setError((e as Error).message)), []);

  useEffect(() => { void loadHistory(); }, [loadHistory]);
  useEffect(() => {
    const id = window.setInterval(() => setNow(serverNow()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const sessions = useMemo(() => history ? eligibleSessions(history) : [], [history]);

  useEffect(() => {
    if (!history || selected) return;
    setSelected(sessions[0]?.id ?? null);
  }, [history, selected, sessions]);

  const loadForm = useCallback((sessionId: number) => {
    setError("");
    return api.get<OutputForm>(`/outputs/${sessionId}`).then((data) => {
      syncServerClock(data.server_now);
      setNow(serverNow());
      setForm(data);
    }).catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    if (recentSessionId) setSelected(recentSessionId);
  }, [recentSessionId]);

  useEffect(() => {
    if (selected) void loadForm(selected);
  }, [selected, loadForm]);

  const secondsRemaining = form ? Math.max(0, Math.floor((new Date(form.locked_at).getTime() - now.getTime()) / 1000)) : 0;
  const locked = Boolean(form?.locked || secondsRemaining <= 0);

  useEffect(() => {
    if (form && !form.locked && secondsRemaining <= 0) {
      void loadForm(form.session_id);
    }
  }, [form, loadForm, secondsRemaining]);

  const updateBag = (code: string, bags: number) => {
    setForm((current) => current ? {
      ...current,
      items: current.items.map((item) => item.code === code ? {...item, bags: Math.max(0, Math.min(9999, Math.floor(bags || 0)))} : item),
    } : current);
  };

  const save = async () => {
    if (!form) return;
    setBusy(true);
    setError("");
    hapticImpact("medium");
    try {
      const payload = Object.fromEntries(form.items.map((item) => [item.code, item.bags]));
      await api.put<OutputSubmit>(`/outputs/${form.session_id}`, {items: payload});
      hapticNotify("success");
      await loadForm(form.session_id);
    } catch (e) {
      hapticNotify("error");
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!history) return error ? <ScreenState kind="error" title="Không tải được sản lượng" message={error} onRetry={loadHistory} /> : <ScreenState kind="loading" title="Đang tải phiên đã ra ca" />;

  return (
    <div className="screen-stack">
      <Card>
        <SectionTitle title="Khai sản lượng" eyebrow="Sau khi ra ca" />
        {sessions.length === 0 ? (
          <p className="muted">Chưa có phiên đã ra ca để khai sản lượng.</p>
        ) : (
          <div className="session-picker">
            {sessions.map((session) => (
              <button key={session.id} type="button" className={selected === session.id ? "active" : ""} onClick={() => setSelected(session.id)}>
                <b>Phiên #{session.id}</b>
                <span>{fmtTime(session.check_in_at)}–{fmtTime(session.check_out_at)}</span>
              </button>
            ))}
          </div>
        )}
      </Card>

      {form && (
        <Card>
          <div className="output-heading">
            <SectionTitle
              title={`Phiên #${form.session_id}`}
              eyebrow={locked ? "Đã khóa chỉnh sửa" : `Còn ${fmtCountdown(secondsRemaining)} để chỉnh sửa`}
            />
            <Chip tone={locked ? "danger" : "success"}>{locked ? "Đã khóa" : "Đang mở"}</Chip>
          </div>
          {locked && <div className="gps-banner gps-banner--warning">Đã khóa chỉnh sửa</div>}
          <div className="product-list">
            {form.items.map((item) => (
              <div key={item.code} className="product-row">
                <span><b>{item.name}</b><small>{item.code} · {fmtKg(item.kg_per_bag)}/túi</small></span>
                <div className="stepper">
                  <button type="button" disabled={locked} onClick={() => updateBag(item.code, item.bags - 1)}>−</button>
                  <input
                    type="number"
                    min="0"
                    max="9999"
                    disabled={locked}
                    value={item.bags}
                    onChange={(event) => updateBag(item.code, Number(event.target.value || 0))}
                  />
                  <button type="button" disabled={locked} onClick={() => updateBag(item.code, item.bags + 1)}>+</button>
                </div>
                <em>{fmtKg(item.bags * item.kg_per_bag)}</em>
              </div>
            ))}
          </div>
          <div className="total-line"><span>Tổng sản lượng</span><b>{fmtKg(totalKg(form.items))}</b></div>
          {error && <p className="form-error">{error}</p>}
          <Button busy={busy} disabled={locked} onClick={save}>Lưu thay đổi</Button>
        </Card>
      )}
    </div>
  );
}
