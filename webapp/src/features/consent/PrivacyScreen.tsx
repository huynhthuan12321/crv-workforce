import {useCallback, useEffect, useState} from "react";
import {api} from "../../api/client";
import {Button, Card, Chip, ScreenState, SectionTitle} from "../../components/ui";
import type {Consent} from "../../types/api";
import {hapticNotify} from "../../lib/haptic";

export function PrivacyScreen({onBack, onConsentChanged}: {onBack: () => void; onConsentChanged: () => void}) {
  const [consent, setConsent] = useState<Consent | undefined>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const load = useCallback(() => api.get<Consent>("/consent/current").then(setConsent).catch((e) => setError((e as Error).message)), []);

  useEffect(() => { void load(); }, [load]);

  const withdraw = async () => {
    setBusy(true);
    setError("");
    try {
      await api.post("/consent/withdraw");
      await load();
      onConsentChanged();
      setConfirming(false);
      hapticNotify("success");
    } catch (e) {
      hapticNotify("error");
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (consent === undefined) return <ScreenState kind="loading" title="Đang tải quyền riêng tư" />;

  return (
    <div className="screen-stack">
      <Button tone="ghost" className="back-button" onClick={onBack}>← Quay lại</Button>
      <Card>
        <SectionTitle eyebrow={consent ? `Phiên bản ${consent.version}` : undefined} title="Quyền riêng tư" />
        <p className="muted">Bạn có quyền xem lại nội dung đã đồng ý và rút lại đồng ý thu thập vị trí bất cứ lúc nào.</p>
        {consent ? <div className="legal-box">{consent.content}</div> : <p>Chưa có nội dung đồng ý.</p>}
        <div className="status-line">
          <span>Trạng thái</span>
          <Chip tone={consent?.accepted ? "success" : "warning"}>{consent?.accepted ? "Đang đồng ý" : "Chưa đồng ý / đã rút"}</Chip>
        </div>
        {confirming && (
          <div className="confirm-box">
            <b>Rút lại đồng ý?</b>
            <p>Sau khi rút, bạn sẽ không thể vào ca mới. Nếu đang trong ca, bạn vẫn được ra ca; quản lý sẽ nhận thông báo.</p>
            <Button tone="danger" busy={busy} onClick={withdraw}>Xác nhận rút lại</Button>
          </div>
        )}
        {error && <p className="form-error">{error}</p>}
        {consent?.accepted && !confirming && <Button tone="warning" onClick={() => setConfirming(true)}>Rút lại đồng ý</Button>}
      </Card>
    </div>
  );
}
