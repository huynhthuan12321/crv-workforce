import {useCallback, useEffect, useState, type ComponentType} from "react";
import {ApiError, api} from "../api/client";
import {ErrorBoundary} from "../components/ErrorBoundary";
import {ScreenState} from "../components/ui";
import {AccessScreen} from "../features/access/AccessScreen";
import {AttendanceScreen} from "../features/attendance/AttendanceScreen";
import {ConsentGate} from "../features/consent/ConsentGate";
import {PrivacyScreen} from "../features/consent/PrivacyScreen";
import {HistoryScreen} from "../features/history/HistoryScreen";
import {EmployeesScreen, PayrollScreen, ReviewScreen, WorkingScreen} from "../features/manager/ManagerScreens";
import {OutputsScreen} from "../features/outputs/OutputsScreen";
import {ReportsScreen} from "../features/director/ReportsScreen";
import {useTelegram} from "../hooks/useTelegram";
import {useKeyboardAvoidance} from "../lib/keyboard";
import type {Employee, TabKey} from "../types/api";
import {AppShell, type SpecialScreen} from "./AppShell";

function useBackButton(active: boolean, onBack: () => void) {
  useEffect(() => {
    const back = window.Telegram?.WebApp?.BackButton;
    if (!back) return;
    if (!active) {
      back.hide();
      return;
    }
    back.show();
    back.onClick(onBack);
    return () => {
      back.offClick(onBack);
      back.hide();
    };
  }, [active, onBack]);
}

const USE_MOCK = import.meta.env.DEV && import.meta.env.VITE_MOCK === "1";

function MockToolbarHost({onChange}: {onChange: () => void}) {
  const [Toolbar, setToolbar] = useState<ComponentType<{onChange: () => void}> | null>(null);

  useEffect(() => {
    if (!USE_MOCK) return;
    let active = true;
    const modulePath = "/src/mock/MockToolbar.tsx";
    void import(/* @vite-ignore */ modulePath).then((module) => {
      if (active) setToolbar(() => module.MockToolbar);
    });
    return () => {
      active = false;
    };
  }, []);

  return Toolbar ? <Toolbar onChange={onChange} /> : null;
}

export function CrvApp() {
  useTelegram();
  useKeyboardAvoidance();
  const [user, setUser] = useState<Employee>();
  const [tab, setTab] = useState<TabKey>("attendance");
  const [special, setSpecial] = useState<SpecialScreen>(null);
  const [loginError, setLoginError] = useState<ApiError | null>(null);
  const [recentOutputSessionId, setRecentOutputSessionId] = useState<number | null>(null);
  const [reviewInitialFilter, setReviewInitialFilter] = useState<"all" | "gps" | "forgot">("all");
  const [reviewInitialSessionId, setReviewInitialSessionId] = useState<number | null>(null);
  const [mockRefresh, setMockRefresh] = useState(0);

  const login = useCallback(async () => {
    setLoginError(null);
    try {
      const data = await api.login();
      const employee = data.employee;
      const start = window.Telegram?.WebApp?.initDataUnsafe?.start_param || "";
      const mockTab = import.meta.env.DEV && import.meta.env.VITE_MOCK === "1"
        ? new URLSearchParams(window.location.search).get("tab") as TabKey | null
        : null;
      const requested = mockTab || (start.startsWith("tab_") ? start.slice(4) as TabKey : null);
      setUser(employee);
      setTab(requested && employee.tabs.includes(requested) ? requested : employee.tabs[0]);
      setSpecial(employee.role === "employee" && !employee.has_location_consent ? "consent" : null);
    } catch (e) {
      setLoginError(e as ApiError);
    }
  }, []);

  useEffect(() => {
    window.Telegram?.WebApp?.ready?.();
    window.Telegram?.WebApp?.expand?.();
    void login();
  }, [login, mockRefresh]);

  const leaveSpecial = useCallback(() => setSpecial(user?.has_location_consent ? null : "consent"), [user]);
  useBackButton(Boolean(special), leaveSpecial);

  if (loginError) {
    return (
      <>
        <MockToolbarHost onChange={() => setMockRefresh((x) => x + 1)} />
        <AccessScreen code={loginError.code} status={loginError.status} onRetry={login} />
      </>
    );
  }

  if (!user) {
    return (
      <main className="app-shell app-shell--center">
        <ScreenState kind="loading" title="Đang xác thực với Telegram" />
      </main>
    );
  }

  const views: Record<TabKey, React.ReactNode> = {
    attendance: <AttendanceScreen onNeedConsent={() => setSpecial("consent")} onCheckedOut={(id) => { setRecentOutputSessionId(id); setTab("outputs"); }} />,
    outputs: <OutputsScreen recentSessionId={recentOutputSessionId} />,
    history: <HistoryScreen />,
    working: <WorkingScreen />,
    review: <ReviewScreen initialFilter={reviewInitialFilter} initialSessionId={reviewInitialSessionId} />,
    payroll: <PayrollScreen onOpenReviewGps={(sessionId) => { setReviewInitialFilter("gps"); setReviewInitialSessionId(sessionId ?? null); setTab("review"); }} />,
    employees: <EmployeesScreen />,
    reports: <ReportsScreen />,
  };

  return (
    <>
      <MockToolbarHost onChange={() => setMockRefresh((x) => x + 1)} />
      <AppShell
        employee={user}
        tab={tab}
        special={special}
        onTab={(next) => { setSpecial(null); setTab(next); }}
        onPrivacy={() => setSpecial("privacy")}
      >
        <ErrorBoundary title="Tab bị lỗi">
          {special === "consent" && <ConsentGate onAccepted={() => { setUser({...user, has_location_consent: true}); setSpecial(null); }} onPrivacy={() => setSpecial("privacy")} />}
          {special === "privacy" && <PrivacyScreen onBack={leaveSpecial} onConsentChanged={() => setUser({...user, has_location_consent: false})} />}
          {!special && views[tab]}
        </ErrorBoundary>
      </AppShell>
    </>
  );
}
