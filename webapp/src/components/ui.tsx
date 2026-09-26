import type {ButtonHTMLAttributes, ReactNode} from "react";

export function Card({children, className = ""}: {children: ReactNode; className?: string}) {
  return <section className={`crv-card ${className}`}>{children}</section>;
}

export function Button({
  children,
  tone = "primary",
  busy = false,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: "primary" | "danger" | "secondary" | "ghost" | "warning";
  busy?: boolean;
}) {
  return (
    <button {...props} disabled={props.disabled || busy} className={`crv-button crv-button--${tone} ${className}`}>
      {busy ? "Đang xử lý..." : children}
    </button>
  );
}

export function Chip({children, tone = "neutral"}: {children: ReactNode; tone?: "neutral" | "success" | "warning" | "danger" | "info"}) {
  return <span className={`chip chip--${tone}`}>{children}</span>;
}

export function ScreenState({
  kind,
  title,
  message,
  onRetry,
}: {
  kind: "loading" | "empty" | "error";
  title: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <Card className={`state state--${kind}`}>
      <div className="state__icon">{kind === "loading" ? <span className="spinner" /> : kind === "empty" ? "∅" : "!"}</div>
      <h2>{title}</h2>
      {message && <p>{message}</p>}
      {onRetry && <Button tone="secondary" onClick={onRetry}>Thử lại</Button>}
    </Card>
  );
}

export function SectionTitle({eyebrow, title, action}: {eyebrow?: string; title: string; action?: ReactNode}) {
  return (
    <div className="section-title">
      <div>
        {eyebrow && <small>{eyebrow}</small>}
        <h2>{title}</h2>
      </div>
      {action}
    </div>
  );
}

export function Metric({label, value, tone = "neutral"}: {label: string; value: ReactNode; tone?: "neutral" | "success" | "warning"}) {
  return (
    <div className={`metric metric--${tone}`}>
      <small>{label}</small>
      <b>{value}</b>
    </div>
  );
}
