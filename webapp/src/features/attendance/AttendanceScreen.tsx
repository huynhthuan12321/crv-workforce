import {useCallback, useEffect, useMemo, useState} from "react";
import {ApiError, api} from "../../api/client";
import {Button, Card, Chip, Metric, ScreenState, SectionTitle} from "../../components/ui";
import {elapsedMinutes, elapsedSeconds, temporarySalary} from "../../lib/clock";
import {appNow, fmtClock, fmtDateLong, fmtDuration, isAfterCheckinCutoff} from "../../lib/date-vn";
import {fmtMoney} from "../../lib/format";
import {hapticImpact, hapticNotify} from "../../lib/haptic";
import {canOpenTelegramLocationSettings, getCurrentLocation, openTelegramLocationSettings} from "../../lib/location";
import type {Today, WorkSession} from "../../types/api";

function gpsText(session?: WorkSession | null) {
  if (!session) return null;
  if (session.flags.includes("gps_out_of_range")) {
    return {tone: "warning" as const, text: `Vị trí ngoài xưởng – đã gắn cờ · cách ${Math.round(session.check_in_distance_m)} m`};
  }
  if (session.flags.includes("gps_low_accuracy")) {
    return {tone: "warning" as const, text: "GPS sai số lớn – đã gắn cờ"};
  }
  return {tone: "success" as const, text: `Trong khu vực xưởng (${Math.round(session.check_in_distance_m)} m)`};
}

export function LocatingScreen({onCancel}: {onCancel: () => void}) {
  return (
    <Card className="locating-card">
      <div className="radar"><span /></div>
      <h2>Đang lấy vị trí của bạn...</h2>
      <p>Vui lòng chờ để phát hiện tọa độ vị trí để chấm công.</p>
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
  const [confirmOut, setConfirmOut] = useState(false);
  const [now, setNow] = useState(() => appNow());

  const load = useCallback(() => api.get<Today>("/attendance/today").then(setToday).catch((e) => setError((e as Error).message)), []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const tick = window.setInterval(() => setNow(appNow()), 1000);
    const refresh = window.setInterval(() => void load(), 60000);
    return () => {
      window.clearInterval(tick);
      window.clearInterval(refresh);
    };
  }, [load]);

  const open = today?.open_session ?? null;
  const minutes = open ? elapsedMinutes(open.check_in_at, now) : 0;
  const salary = open ? temporarySalary(minutes, open.rate_snapshot) : today?.estimated_day_amount ?? 0;
  const afterCutoff = !open && isAfterCheckinCutoff(now);
  const gps = gpsText(open);

  const runAction = async () => {
    if (!today) return;
    if (today.open_session && !confirmOut) {
      setConfirmOut(true);
      return;
    }
    setBusy(true);
    setError("");
    setLocating(true);
    hapticImpact("medium");
    try {
      const location = await getCurrentLocation();
      const kind = today.open_session ? "check-out" : "check-in";
      const session = await api.post<WorkSession>(`/attendance/${kind}`, location);
      hapticNotify("success");
      if (kind === "check-out") onCheckedOut(session.id);
      await load();
      setConfirmOut(false);
    } catch (e) {
      const err = e as ApiError | Error;
      hapticNotify("error");
      if (err instanceof ApiError && err.code === "LOCATION_CONSENT_REQUIRED") onNeedConsent();
      else setError(err.message);
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
              <p>Hệ thống sẽ lấy vị trí hiện tại và khóa thời điểm ra ca theo giờ máy chủ.</p>
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
        <div className="hero-card__top">
          <div>
            <small>Chấm công · Chưa vào ca</small>
            <h2>{fmtDateLong(now)}</h2>
          </div>
          <Chip tone={afterCutoff ? "warning" : "info"}>{afterCutoff ? "Đã qua giờ" : "Sẵn sàng"}</Chip>
        </div>
        <div className="clock-illustration">{afterCutoff ? "☾" : "▶"}</div>
        <h2>{afterCutoff ? "Đã qua 18:00" : "Sẵn sàng làm việc!"}</h2>
        <p className="muted">{afterCutoff ? "Không thể vào ca từ 18:00. Vui lòng quay lại vào ngày mai." : "Nhấn nút để vào ca. Backend sẽ kiểm tra giờ máy chủ và vị trí GPS."}</p>
        {error && <p className="form-error">{error}</p>}
        <Button className="round-action" disabled={afterCutoff} busy={busy} onClick={runAction}>VÀO CA</Button>
      </Card>
    </div>
  );
}
