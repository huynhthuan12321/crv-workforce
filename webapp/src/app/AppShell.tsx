import type {ReactNode} from "react";
import type {Employee, TabKey} from "../types/api";
import {Chip} from "../components/ui";
import {roleLabels, tabIcons, tabLabels} from "./labels";

export type SpecialScreen = "privacy" | "consent" | null;

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
          <button className="icon-button" type="button" onClick={onPrivacy} aria-label="Quyền riêng tư">ⓘ</button>
        )}
      </header>
      {children}
      {!special && (
        <nav className="bottom-tabs">
          {employee.tabs.map((item) => (
            <button key={item} type="button" className={tab === item ? "active" : ""} onClick={() => onTab(item)}>
              <span>{tabIcons[item]}</span>
              <em>{tabLabels[item]}</em>
            </button>
          ))}
        </nav>
      )}
    </main>
  );
}
