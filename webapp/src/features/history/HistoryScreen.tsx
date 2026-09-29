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
  co_co_gps: "Có vị trí cần quản lý xem lại",
  cho_duyet: "Chờ duyệt",
};

export function groupHistorySessions(sessions: HistorySession[]) {
  return {
    pendingEligible: sessions.filter((row) => row.payroll_group === "pending_eligible"
      || (!row.payroll_group && !row.pay_batch_id && row.status === "closed" && row.pending_reason !== "co_co_gps")),
    blockedGps: sessions.filter((row) => row.payroll_group === "blocked_gps"
      || (!row.payroll_group && !row.pay_batch_id && row.status === "closed"
        && (row.pending_reason === "co_co_gps" || Boolean(row.flags?.length)))),
    openOrReview: sessions.filter((row) => row.payroll_group === "open_or_review"
      || (!row.payroll_group && !row.pay_batch_id && (row.status === "open" || row.status === "needs_review"))),
  };
}

function SessionList({sessions, showReason = false}: {sessions: HistorySession[]; showReason?: boolean}) {
  return (
    <div className="session-list">
      {sessions.map((session) => (
        <div key={session.id} className="session-row">
          <div>
            <b className="session-time">{fmtTime(session.check_in_at)}–{fmtTime(session.check_out_at)}</b>
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

function UnpaidGroups({sessions, pending, blocked}: {sessions: HistorySession[]; pending: number; blocked: number}) {
  const groups = groupHistorySessions(sessions);
  return (
    <>
      <div className="history-block">
        <div className="history-block__head"><b>Chờ duyệt</b><Chip tone="warning">{fmtMoney(pending)}</Chip></div>
        {groups.pendingEligible.length === 0
          ? <p className="muted">Không có phiên đủ điều kiện duyệt.</p>
          : <SessionList sessions={groups.pendingEligible} showReason />}
      </div>
      <div className="history-block">
        <div className="history-block__head"><b>Chờ quản lý xem lại vị trí</b><Chip tone="warning">{fmtMoney(blocked)}</Chip></div>
        {groups.blockedGps.length === 0
          ? <p className="muted">Không có phiên cần xem lại vị trí.</p>
          : <SessionList sessions={groups.blockedGps} showReason />}
      </div>
      <div className="history-block">
        <div className="history-block__head"><b>Đang mở / Quên ra ca</b></div>
        {groups.openOrReview.length === 0
          ? <p className="muted">Không có phiên đang mở hoặc quên ra ca.</p>
          : <SessionList sessions={groups.openOrReview} showReason />}
      </div>
    </>
  );
}

export function HistoryScreen() {
  const [history, setHistory] = useState<History>();
  const [error, setError] = useState("");
  const load = useCallback(() => api.get<History>("/history").then(setHistory).catch((e) => setError((e as Error).message)), []);

  useEffect(() => { void load(); }, [load]);
  if (!history) return error
    ? <ScreenState kind="error" title="Không tải được lịch sử" message={error} onRetry={load} />
    : <ScreenState kind="loading" title="Đang tải lịch sử" />;
  if (history.days.length === 0) return <ScreenState kind="empty" title="Chưa có dữ liệu" message="Các phiên làm, đợt đã trả và khoản chờ duyệt sẽ hiện ở đây." />;

  return (
    <div className="screen-stack">
      {history.days.map((day) => (
        <Card key={day.date}>
          <SectionTitle eyebrow={fmtDateLong(`${day.date}T00:00:00+07:00`)} title={fmtMoney(day.total_amount)} />
          <div className="mini-grid">
            <div className="metric metric--success"><small>Đã trả</small><b>{fmtMoney(day.paid_amount)}</b></div>
            <div className="metric metric--warning"><small>Chờ duyệt</small><b>{fmtMoney(day.pending_amount)}</b></div>
            <div className="metric metric--info"><small>Chờ quản lý xem lại</small><b>{fmtMoney(day.blocked_amount)}</b></div>
          </div>
          {day.blocked_amount > 0 && <p className="muted">Có phiên cần quản lý xem lại vị trí trước khi duyệt.</p>}
          {day.batches.map((batch) => (
            <div key={batch.id} className="history-block history-block--paid">
              <div className="history-block__head"><b>Đợt {batch.batch_no} · Đã trả</b><Chip tone="success">{fmtMoney(batch.amount)}</Chip></div>
              <SessionList sessions={batch.sessions} />
            </div>
          ))}
          {day.unpaid_sessions.length > 0 && <UnpaidGroups sessions={day.unpaid_sessions} pending={day.pending_amount} blocked={day.blocked_amount} />}
        </Card>
      ))}
    </div>
  );
}
