import {useCallback, useEffect, useState} from "react";
import {api} from "../../api/client";
import {Button, Card, Chip, ScreenState, SectionTitle} from "../../components/ui";
import {useKeyboardAvoidance} from "../../lib/keyboard";

type Announcement = {
  id: number;
  sender_role: string;
  sender_id: number;
  audience_type: string;
  body: string;
  created_at: string | null;
  recipient_count: number;
  acknowledged_count: number;
};

type Conversation = {
  id: number;
  employee_code: string;
  employee_name: string;
  channel: "manager" | "director";
};

type ConversationMessage = {
  id: number;
  sender_id: number;
  direction: string;
  body: string;
  created_at: string | null;
};

export function MessagesScreen({role}: {role: "manager" | "director"}) {
  useKeyboardAvoidance();
  const [mode, setMode] = useState<"announcements" | "inbox" | "compose">("announcements");
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [body, setBody] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      setError("");
      setAnnouncements(await api.get<Announcement[]>("/announcements"));
      setConversations(await api.get<Conversation[]>(`/conversations?channel=${role === "director" ? "director" : "manager"}`));
    } catch (err) {
      setError((err as Error).message);
    }
  }, [role]);
  useEffect(() => { void load(); }, [load]);
  const openConversation = async (conversation: Conversation) => {
    setSelected(conversation);
    setMessages(await api.get<ConversationMessage[]>(`/conversations/${conversation.id}/messages`));
  };
  const send = async () => {
    if (!selected || body.trim().length === 0) return;
    await api.post(`/conversations/${selected.id}/messages`, {body});
    setBody("");
    await openConversation(selected);
  };
  if (error) return <ScreenState kind="error" title="Không tải được tin nhắn" message={error} onRetry={load} />;
  if (selected) return (
    <div className="screen-stack">
      <Button tone="ghost" onClick={() => setSelected(null)}>← Quay lại hộp thư</Button>
      <Card>
        <SectionTitle eyebrow={selected.channel === "manager" ? "Kênh Quản lý" : "Kênh Giám đốc"} title={`${selected.employee_code} · ${selected.employee_name}`} />
        <div className="message-thread">
          {messages.map((item) => <div key={item.id} className={`message-bubble ${item.direction === "to_staff" ? "message-bubble--right" : ""}`}>{item.body}</div>)}
        </div>
        {!(role === "director" && selected.channel === "manager") && (
          <div className="message-compose">
            <textarea aria-label="Nội dung trả lời" maxLength={2000} value={body} onChange={(event) => setBody(event.target.value)} placeholder="Viết tin nhắn…" />
            <Button disabled={!body.trim()} onClick={send}>Gửi</Button>
          </div>
        )}
        {role === "director" && selected.channel === "manager" && <p className="muted">Bạn chỉ có quyền xem kênh Quản lý.</p>}
      </Card>
    </div>
  );
  return (
    <div className="screen-stack">
      <SectionTitle eyebrow="Tin nhắn" title="Thông báo và hộp thư" />
      <div className="segmented-control">
        <Button tone={mode === "announcements" ? "primary" : "secondary"} onClick={() => setMode("announcements")}>Thông báo</Button>
        <Button tone={mode === "inbox" ? "primary" : "secondary"} onClick={() => setMode("inbox")}>Hộp thư</Button>
      </div>
      {mode === "compose" ? <ComposeAnnouncement role={role} onDone={() => { setMode("announcements"); void load(); }} /> : mode === "announcements" ? (
        <>
          <Button onClick={() => setMode("compose")}>📢 Soạn thông báo</Button>
          {announcements.map((item) => <Card key={item.id}>
            <div className="row-between">
              <Chip tone="info">{item.sender_role === "director" ? "Giám đốc" : "Quản lý"}</Chip>
              <small>{item.acknowledged_count}/{item.recipient_count} đã nhận</small>
            </div>
            <p>{item.body}</p>
          </Card>)}
          {announcements.length === 0 && <ScreenState kind="empty" title="Chưa có thông báo" />}
        </>
      ) : (
        conversations.map((conversation) => <Card key={conversation.id} className="clickable-card" onClick={() => void openConversation(conversation)}><b>{conversation.employee_code} · {conversation.employee_name}</b><small>{conversation.channel === "manager" ? "Kênh Quản lý" : "Kênh Giám đốc"}</small></Card>)
      )}
    </div>
  );
}

function ComposeAnnouncement({role, onDone}: {role: "manager" | "director"; onDone: () => void}) {
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState<"all" | "managers" | "employees" | "location" | "custom">("employees");
  const [error, setError] = useState("");
  const [result, setResult] = useState("");
  const send = async () => {
    try {
      const response = await api.post<{recipient_count: number; skipped_count: number}>("/announcements", {body, audience_type: audience});
      setResult(`Đã gửi tới ${response.recipient_count} người${response.skipped_count ? ` · bỏ qua ${response.skipped_count} người` : ""}.`);
      setTimeout(onDone, 350);
    } catch (err) {
      setError((err as Error).message);
    }
  };
  return <Card>
    <SectionTitle eyebrow="Soạn thông báo" title={role === "director" ? "Gửi thông báo" : "Gửi nhân viên"} />
    <label className="form-field">Đối tượng
      <select value={audience} onChange={(event) => setAudience(event.target.value as typeof audience)}>
        <option value="employees">Tất cả nhân viên</option>
        {role === "director" && <option value="managers">Chỉ quản lý</option>}
        {role === "director" && <option value="all">Tất cả</option>}
        <option value="location">Theo kho</option>
        <option value="custom">Chọn từng người</option>
      </select>
    </label>
    <label className="form-field">Nội dung<textarea maxLength={2000} value={body} onChange={(event) => setBody(event.target.value)} /></label>
    {error && <p className="form-error">{error}</p>}
    {result && <p className="form-success">{result}</p>}
    <Button disabled={!body.trim()} onClick={send}>Gửi thông báo</Button>
  </Card>;
}
