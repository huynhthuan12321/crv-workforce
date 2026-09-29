import type {ReactNode} from "react";
import type {Employee, TabKey} from "../types/api";
import {Chip} from "../components/ui";
import {roleLabels, tabLabels} from "./labels";

export type SpecialScreen = "privacy" | "consent" | null;

function TabIcon({tab}: {tab: TabKey}) {
  const common = {fill: "none", stroke: "currentColor", strokeLinecap: "round" as const, strokeLinejoin: "round" as const, strokeWidth: 2};
  const paths: Record<TabKey, ReactNode> = {
    attendance: <><circle cx="12" cy="12" r="8" /><path d="M12 8v4l2.5 1.5" /></>,
    outputs: <><path d="M4 8.5 12 4l8 4.5-8 4.5L4 8.5Z" /><path d="M4 13.5 12 18l8-4.5" /><path d="M12 13v5" /></>,
    history: <><path d="M4 12a8 8 0 1 0 2.35-5.65" /><path d="M4 5v4h4" /><path d="M12 8v4l3 2" /></>,
    working: <><circle cx="12" cy="12" r="8" /><path d="M9 12h6" /><path d="M12 9v6" /></>,
    review: <><path d="M12 4 3.5 19h17L12 4Z" /><path d="M12 9v4" /><path d="M12 16h.01" /></>,
    payroll: <><path d="M7 7h10" /><path d="M7 12h10" /><path d="M7 17h6" /><path d="M5 4h14v16H5z" /></>,
    employees: <><path d="M16 19v-1.5A3.5 3.5 0 0 0 12.5 14h-5A3.5 3.5 0 0 0 4 17.5V19" /><circle cx="10" cy="8" r="3" /><path d="M20 19v-1a3 3 0 0 0-2-2.8" /><path d="M17 5.3a3 3 0 0 1 0 5.4" /></>,
    reports: <><path d="M4 19V5" /><path d="M4 19h16" /><path d="M8 16v-5" /><path d="M12 16V8" /><path d="M16 16v-3" /></>,
    messages: <><rect x="4" y="5" width="16" height="14" rx="3" /><path d="m7 9 5 3 5-3" /></>,
  };
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" {...common}>
      {paths[tab]}
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <circle cx="12" cy="12" r="8" />
      <path d="M12 11v5" />
      <path d="M12 8h.01" />
    </svg>
  );
}

export function AppShell({
  employee,
  tab,
  special,
  onTab,
  onPrivacy,
  children,
}: {
  employee: Employee;
  tab: TabKey;
  special: SpecialScreen;
  onTab: (tab: TabKey) => void;
  onPrivacy: () => void;
  children: ReactNode;
}) {
  const initials = employee.full_name.split(/\s+/).slice(-2).map((part) => part[0]).join("").toUpperCase();
  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="avatar">{initials || "CR"}</div>
        <div className="topbar__identity">
          <small>CRV WORKFORCE</small>
          <h1>{employee.full_name}</h1>
          <div className="topbar__meta">
            <Chip tone="info">{employee.code}</Chip>
            <Chip tone="neutral">{roleLabels[employee.role]}</Chip>
          </div>
        </div>
        {employee.role === "employee" && (
          <button className="icon-button" type="button" onClick={onPrivacy} aria-label="Quyền riêng tư"><InfoIcon /></button>
        )}
      </header>
      {children}
      {!special && (
        <nav className="bottom-tabs">
          {employee.tabs.map((item) => (
            <button key={item} type="button" className={tab === item ? "active" : ""} onClick={() => onTab(item)}>
              <span><TabIcon tab={item} /></span>
              <em>{tabLabels[item]}</em>
            </button>
          ))}
        </nav>
      )}
    </main>
  );
}
