import {useCallback, useEffect, useState} from "react";
import {api} from "../../api/client";
import {Button, Card, ScreenState, SectionTitle} from "../../components/ui";
import type {Consent} from "../../types/api";
import {hapticNotify} from "../../lib/haptic";

export function ConsentGate({onAccepted, onPrivacy}: {onAccepted: () => void; onPrivacy: () => void}) {
  const [consent, setConsent] = useState<Consent | undefined>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get<Consent>("/consent/current").then(setConsent).catch((e) => setError((e as Error).message)), []);

  useEffect(() => { void load(); }, [load]);

  const accept = async () => {
    if (!consent) return;
    setBusy(true);
    setError("");
    try {
      await api.post("/consent", {version: consent.version});
      hapticNotify("success");
      onAccepted();
    } catch (e) {
      hapticNotify("error");
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (consent === undefined) return <ScreenState kind="loading" title="Đang tải thông báo quyền riêng tư" />;
  if (!consent) {
    return (
      <ScreenState
        kind="error"
        title="Chưa có nội dung đồng ý"
        message="Vui lòng liên hệ quản lý để cấu hình thông báo thu thập vị trí."
        onRetry={load}
      />
    );
  }

  return (
    <Card className="consent-card">
      <SectionTitle eyebrow={`Phiên bản ${consent.version}`} title="Đồng ý thu thập vị trí" />
      <div className="legal-box">{consent.content}</div>
      {error && <p className="form-error">{error}</p>}
      <Button busy={busy} onClick={accept}>Tôi đồng ý</Button>
      <Button tone="ghost" onClick={onPrivacy}>Xem quyền riêng tư</Button>
    </Card>
  );
}
