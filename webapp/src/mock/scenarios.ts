import type {Consent, Employee, History, OutputForm, Today, WorkSession} from "../types/api";

export type MockScenario =
  | "idle"
  | "locating"
  | "open"
  | "open_far"
  | "after_cutoff"
  | "output_editable"
  | "output_locked"
  | "history_multi"
  | "consent"
  | "not_registered"
  | "locked"
  | "expired"
  | "network";

export const mockScenarios: Array<{key: MockScenario; label: string}> = [
  {key: "idle", label: "Chưa vào ca"},
  {key: "locating", label: "Đang lấy vị trí"},
  {key: "open", label: "Trong ca"},
  {key: "open_far", label: "GPS ngoài 250m"},
  {key: "after_cutoff", label: "Sau 18:00"},
  {key: "output_editable", label: "SL còn 10 phút"},
  {key: "output_locked", label: "SL đã khóa"},
  {key: "history_multi", label: "Lịch sử nhiều đợt"},
  {key: "consent", label: "Chưa đồng ý"},
  {key: "not_registered", label: "Chưa cấp quyền"},
  {key: "locked", label: "Bị khóa"},
  {key: "expired", label: "Hết phiên"},
  {key: "network", label: "Lỗi mạng"},
];

export const mockEmployee: Employee = {
  id: 1,
  code: "NV001",
  full_name: "Nguyễn Văn A",
  role: "employee",
  tabs: ["attendance", "outputs", "history"],
  has_location_consent: true,
};

export const mockConsent: Consent = {
  version: 1,
  accepted: true,
  effective_at: "2026-04-01T00:00:00+07:00",
  content: "CRV thu thập vị trí GPS chỉ tại thời điểm bạn bấm Vào ca/Ra ca để xác nhận việc chấm công tại xưởng. Dữ liệu dùng cho chấm công, xử lý phiên bất thường và trả lương; không theo dõi liên tục.",
};

export const openSession: WorkSession = {
  id: 101,
  employee_id: 1,
  work_date: "2024-04-24",
  check_in_at: "2024-04-24T06:12:00+07:00",
  check_out_at: null,
  minutes: null,
  rate_snapshot: 30000,
  amount_raw: null,
  status: "open",
  flags: [],
  check_in_distance_m: 12,
  check_out_distance_m: null,
};

export const closedSession: WorkSession = {
  ...openSession,
  id: 102,
  check_out_at: "2024-04-24T11:35:00+07:00",
  minutes: 323,
  amount_raw: 161500,
  status: "closed",
};

export const mockProducts = [
  {code: "BOT", name: "Bột", kg_per_bag: 1.2, bags: 5},
  {code: "XUC_XICH", name: "Xúc xích", kg_per_bag: 1, bags: 3},
  {code: "PHO_MAI", name: "Phô mai", kg_per_bag: 1, bags: 2},
  {code: "CHA_BONG", name: "Chà bông", kg_per_bag: 1, bags: 1},
  {code: "SOT_CAM", name: "Sốt cam", kg_per_bag: 2, bags: 1},
  {code: "SOT_TRANG", name: "Sốt trắng", kg_per_bag: 2, bags: 0},
  {code: "BO", name: "Bơ", kg_per_bag: 2, bags: 0},
];

export function scenarioFromUrl(): MockScenario {
  const value = new URLSearchParams(window.location.search).get("scenario") as MockScenario | null;
  return value && mockScenarios.some((item) => item.key === value) ? value : "idle";
}

export function todayForScenario(scenario: MockScenario): Today {
  if (scenario === "open" || scenario === "locating") {
    return {open_session: openSession, estimated_day_amount: 104000, paid_today: 0};
  }
  if (scenario === "open_far") {
    return {open_session: {...openSession, flags: ["gps_out_of_range"], check_in_distance_m: 250}, estimated_day_amount: 68000, paid_today: 0};
  }
  return {open_session: null, estimated_day_amount: 0, paid_today: 0};
}

export function outputForScenario(scenario: MockScenario, sessionId = 102): OutputForm {
  return {
    session_id: sessionId,
    locked: scenario === "output_locked",
    seconds_remaining: scenario === "output_locked" ? 0 : 572,
    locked_at: scenario === "output_locked" ? "2024-04-24T11:45:00+07:00" : new Date(Date.now() + 572000).toISOString(),
    items: mockProducts,
  };
}

export const mockHistory: History = {
  from: "2024-04-23",
  to: "2024-04-24",
  days: [
    {
      date: "2024-04-24",
      total_amount: 284000,
      batches: [
        {id: 1, batch_no: 1, amount: 162000, approved_at: "2024-04-24T12:00:00+07:00", sessions: [{...closedSession, output: [] as const, pay_batch_id: 1, pending_reason: null}]},
      ],
      unpaid_sessions: [
        {
          ...closedSession,
          id: 103,
          check_in_at: "2024-04-24T13:05:00+07:00",
          check_out_at: "2024-04-24T17:10:00+07:00",
          minutes: 245,
          amount_raw: 122500,
          pay_batch_id: null,
          pending_reason: "cho_duyet",
          output: mockProducts.map((item) => ({code: item.code, name: item.name, bags: item.bags, kg: item.bags * item.kg_per_bag})),
        },
      ],
    },
    {
      date: "2024-04-23",
      total_amount: 248000,
      batches: [
        {id: 2, batch_no: 1, amount: 248000, approved_at: "2024-04-23T18:00:00+07:00", sessions: []},
      ],
      unpaid_sessions: [],
    },
  ],
};
