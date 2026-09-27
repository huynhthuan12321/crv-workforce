import {useCallback, useEffect, useState} from "react";
import {api} from "../../api/client";
import {Card, Chip, ScreenState, SectionTitle} from "../../components/ui";
import {fmtDateLong, fmtTime, fmtDuration} from "../../lib/date-vn";
import {fmtKg, fmtMoney, totalKg} from "../../lib/format";
import {gpsLabel} from "../../lib/gps-label";
import type {History, HistorySession} from "../../types/api";

const reasonLabels: Record<string, string> = {
  dang_mo: "Đang mở",
  cho_xu_ly: "Chờ xử lý",
  co_co_gps: "Có cờ GPS chưa xử lý",
  cho_duyet: "Chờ duyệt",
};

function SessionList({sessions, showReason = false}: {sessions: HistorySession[]; showReason?: boolean}) {
  return (
    <div className="session-list">
      {sessions.map((session) => (
        <div key={session.id} className="session-row">
          <div>
            <b>{fmtTime(session.check_in_at)}–{fmtTime(session.check_out_at)}</b>
            <small>{session.minutes == null ? "Chưa tính phút" : fmtDuration(session.minutes)}</small>
            {session.output?.length > 0 && <small>Sản lượng: {fmtKg(totalKg(session.output))}</small>}
          </div>
          <div className="session-row__right">
            <Chip tone={session.flags?.length ? "warning" : "success"}>{gpsLabel(session)}</Chip>
            {showReason && session.pending_reason && <Chip tone="neutral">{reasonLabels[session.pending_reason] || session.pending_reason}</Chip>}
          </div>
        </div>
      ))}
    </div>
  );
}

export function HistoryScreen() {
  const [history, setHistory] = useState<History>();
  const [error, setError] = useState("");
  const load = useCallback(() => api.get<History>("/history").then(setHistory).catch((e) => setError((e as Error).message)), []);

  useEffect(() => { void load(); }, [load]);

  if (!history) return error ? <ScreenState kind="error" title="Không tải được lịch sử" message={error} onRetry={load} /> : <ScreenState kind="loading" title="Đang tải lịch sử" />;
  if (history.days.length === 0) return <ScreenState kind="empty" title="Chưa có dữ liệu" message="Các phiên làm, đợt đã trả và khoản chờ duyệt sẽ hiện ở đây." />;

  return (
    <div className="screen-stack">
      {history.days.map((day) => {
        const paid = day.paid_amount;
        const pending = day.pending_amount;
        const blocked = day.blocked_amount;
        return (
          <Card key={day.date}>
            <SectionTitle eyebrow={fmtDateLong(`${day.date}T00:00:00+07:00`)} title={fmtMoney(day.total_amount)} />
            <div className="mini-grid">
              <div className="metric metric--success"><small>Đã trả</small><b>{fmtMoney(paid)}</b></div>
              <div className="metric metric--warning"><small>Chờ duyệt</small><b>{fmtMoney(pending)}</b></div>
              <div className="metric metric--info"><small>Chờ quản lý xem lại</small><b>{fmtMoney(blocked)}</b></div>
            </div>
            {blocked > 0 && <p className="muted">Có phiên cần quản lý xem lại vị trí trước khi duyệt.</p>}
            {day.batches.map((batch) => (
              <div key={batch.id} className="history-block history-block--paid">
                <div className="history-block__head"><b>Đợt {batch.batch_no} · Đã trả</b><Chip tone="success">{fmtMoney(batch.amount)}</Chip></div>
                <SessionList sessions={batch.sessions} />
              </div>
            ))}
            {day.unpaid_sessions.length > 0 && (
              <div className="history-block">
                <div className="history-block__head">
                  <b>Chờ duyệt</b>
                  <Chip tone="warning">{fmtMoney(pending)}</Chip>
                </div>
                <SessionList sessions={day.unpaid_sessions} showReason />
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}
