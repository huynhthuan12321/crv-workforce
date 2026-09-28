import {useCallback, useEffect, useMemo, useState} from "react";
import {ApiError, api} from "../../api/client";
import {Button, Card, Chip, Metric, ScreenState} from "../../components/ui";
import {elapsedMinutes, elapsedSeconds, temporarySalary} from "../../lib/clock";
import {fmtClock, fmtDateLong, fmtDuration} from "../../lib/date-vn";
import {fmtMoney} from "../../lib/format";
import {gpsLabel} from "../../lib/gps-label";
import {hapticImpact, hapticNotify} from "../../lib/haptic";
import {canOpenTelegramLocationSettings, getCurrentLocation, openTelegramLocationSettings} from "../../lib/location";
import {serverNow, syncServerClock} from "../../lib/server-clock";
import type {Today, WorkSession} from "../../types/api";

function CheckInIcon({done = false}: {done?: boolean}) {
  if (done) {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.4">
        <path d="M20 6 9 17l-5-5" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <circle cx="12" cy="12" r="8" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function gpsText(session?: WorkSession | null) {
  if (!session) return null;
  if (session.flags.includes("gps_out_of_range")) {
    return {tone: "warning" as const, text: `⚠ ${gpsLabel(session)}. Vẫn ghi nhận vào ca và gửi quản lý kiểm tra.`};
  }
  if (session.flags.includes("gps_low_accuracy")) {
    return {tone: "warning" as const, text: `⚠ ${gpsLabel(session)}. Vẫn ghi nhận vào ca và gửi quản lý kiểm tra.`};
  }
  return {tone: "success" as const, text: gpsLabel(session)};
}

function actionErrorMessage(error: ApiError | Error): string {
  if (!(error instanceof ApiError) && ["LOCATION_DENIED", "LOCATION_UNSUPPORTED"].includes(error.message)) {
    return "Không lấy được vị trí. Thử lại.";
  }
  return error.message;
}

export function LocatingScreen({onCancel}: {onCancel: () => void}) {
  return (
    <Card className="locating-card">
      <div className="radar"><span /></div>
      <h2>Đang lấy vị trí của bạn...</h2>
      <p>Vui lòng chờ để xác định vị trí của bạn khi chấm công.</p>
      <ul className="note-list">
        <li>Nếu không thấy yêu cầu quyền: iPhone/Android → Vị trí → Cho phép.</li>
        <li>Telegram Desktop có thể không hỗ trợ vị trí chính xác.</li>
      </ul>
      {canOpenTelegramLocationSettings() && <Button tone="secondary" onClick={openTelegramLocationSettings}>Mở cài đặt vị trí</Button>}
      <Button tone="ghost" onClick={onCancel}>Hủy</Button>
    </Card>
  );
}

export function AttendanceScreen({onNeedConsent, onCheckedOut}: {onNeedConsent: () => void; onCheckedOut: (sessionId: number) => void}) {
  const [today, setToday] = useState<Today>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [locating, setLocating] = useState(false);
  const [checkInDone, setCheckInDone] = useState(false);
  const [confirmOut, setConfirmOut] = useState(false);
  const [now, setNow] = useState(() => serverNow());

  const load = useCallback(() => api.get<Today>("/attendance/today").then((data) => {
    syncServerClock(data.server_now);
    setNow(serverNow());
    setToday(data);
  }).catch((e) => setError((e as Error).message)), []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const tick = window.setInterval(() => setNow(serverNow()), 1000);
    const refresh = window.setInterval(() => void load(), 60000);
    return () => {
      window.clearInterval(tick);
      window.clearInterval(refresh);
    };
  }, [load]);

  const open = today?.open_session ?? null;
  const minutes = open ? elapsedMinutes(open.check_in_at, now) : 0;
  const salary = open ? temporarySalary(minutes, open.rate_snapshot) : today?.estimated_day_amount ?? 0;
  const afterCutoff = !open && today ? !today.can_check_in : false;
  const gps = gpsText(open);

  const runAction = async () => {
    if (!today) return;
    if (today.open_session && !confirmOut) {
      setConfirmOut(true);
      return;
    }
    setBusy(true);
    setError("");
    setCheckInDone(false);
    hapticImpact("medium");
    try {
      const location = await getCurrentLocation();
      const kind = today.open_session ? "check-out" : "check-in";
      const session = await api.post<WorkSession>(`/attendance/${kind}`, location);
      hapticNotify("success");
      if (kind === "check-out") onCheckedOut(session.id);
      if (kind === "check-in") {
        setCheckInDone(true);
        await new Promise((resolve) => window.setTimeout(resolve, 260));
      }
      await load();
      setConfirmOut(false);
    } catch (e) {
      const err = e as ApiError | Error;
      hapticNotify("error");
      if (err instanceof ApiError && err.code === "LOCATION_CONSENT_REQUIRED") onNeedConsent();
      else setError(actionErrorMessage(err));
    } finally {
      setBusy(false);
      setLocating(false);
    }
  };

  const elapsed = useMemo(() => open ? fmtClock(elapsedSeconds(open.check_in_at, now)) : "00:00:00", [open, now]);

  if (locating || (import.meta.env.DEV && import.meta.env.VITE_MOCK === "1" && new URLSearchParams(window.location.search).get("scenario") === "locating")) {
    return <LocatingScreen onCancel={() => setLocating(false)} />;
  }
  if (!today) return error ? <ScreenState kind="error" title="Không tải được chấm công" message={error} onRetry={load} /> : <ScreenState kind="loading" title="Đang tải dữ liệu chấm công" />;

  if (open) {
    return (
      <div className="screen-stack">
        <Card className="hero-card hero-card--open">
          <div className="hero-card__top">
            <div>
              <small>Đang trong ca</small>
              <h2>{fmtDateLong(open.check_in_at)}</h2>
            </div>
            <Chip tone="success">Đang trong ca</Chip>
          </div>
          {gps && <div className={`gps-banner gps-banner--${gps.tone}`}>{gps.text}</div>}
          {open.location_name_snapshot && <p className="location-note">Kho: <b>{open.location_code_snapshot} · {open.location_name_snapshot}</b></p>}
          <div className="timer-block">
            <span>Vào ca lúc</span>
            <b>{new Intl.DateTimeFormat("vi-VN", {timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit", hour12: false}).format(new Date(open.check_in_at))}</b>
            <strong>{elapsed}</strong>
          </div>
          <div className="money-block">
            <small>Lương tạm tính hôm nay</small>
            <span>{fmtMoney(salary)}</span>
            <p>({minutes} phút × {fmtMoney(open.rate_snapshot)}/giờ)</p>
          </div>
          <div className="mini-grid">
            <Metric label="Thời lượng" value={fmtDuration(minutes)} />
            <Metric label="Đã trả hôm nay" value={fmtMoney(today.paid_today)} tone="success" />
          </div>
          {confirmOut && (
            <div className="confirm-box">
              <b>Xác nhận ra ca?</b>
              <p>Ứng dụng sẽ lấy vị trí hiện tại và ghi nhận giờ ra ca theo giờ hệ thống.</p>
            </div>
          )}
          {error && <p className="form-error">{error}</p>}
          <Button tone="danger" busy={busy} onClick={runAction}>{confirmOut ? "Xác nhận ra ca" : "RA CA"}</Button>
          {confirmOut && <Button tone="ghost" onClick={() => setConfirmOut(false)}>Hủy</Button>}
        </Card>
      </div>
    );
  }

  return (
    <div className="screen-stack">
      <Card className={`hero-card ${afterCutoff ? "hero-card--locked" : ""}`}>
        <div className="hero-card__top hero-card__top--status">
          <div>
            <small>Chấm công · Chưa vào ca</small>
            <h2 className="hero-card__date">{fmtDateLong(now)}</h2>
          </div>
          <span className={`status-pill ${afterCutoff ? "status-pill--locked" : "status-pill--ready"}`}>
            <i aria-hidden="true" />
            {afterCutoff ? "Đã qua giờ" : "Sẵn sàng"}
          </span>
        </div>
        <h2 className="hero-card__headline">{afterCutoff ? `Đã qua ${today.checkin_cutoff}` : "Sẵn sàng làm việc!"}</h2>
        {today.work_location && <p className="location-note">Kho hôm nay: <b>{today.work_location.code} · {today.work_location.name}</b></p>}
        <p className="muted">{afterCutoff ? `Không thể vào ca từ ${today.checkin_cutoff}. Vui lòng quay lại vào ngày mai.` : "Nhấn VÀO CA khi bắt đầu làm việc. Ứng dụng sẽ lấy vị trí của bạn tại thời điểm này."}</p>
        {error && <p className="form-error">{error}</p>}
        <button
          type="button"
          className="round-action"
          disabled={!today.can_check_in || busy}
          aria-disabled={!today.can_check_in || busy}
          onClick={runAction}
        >
          {busy ? (
            <>
              <span className="round-action__spinner" aria-hidden="true" />
              <span>Đang lấy vị trí...</span>
            </>
          ) : checkInDone ? (
            <>
              <span className="round-action__icon round-action__icon--svg"><CheckInIcon done /></span>
              <span>ĐÃ VÀO CA</span>
            </>
          ) : (
            <>
              <span className="round-action__icon round-action__icon--svg"><CheckInIcon /></span>
              <span>VÀO CA</span>
            </>
          )}
        </button>
        {!afterCutoff && <small className="action-hint">Có thể vào ca trước {today.checkin_cutoff}</small>}
      </Card>
    </div>
  );
}
