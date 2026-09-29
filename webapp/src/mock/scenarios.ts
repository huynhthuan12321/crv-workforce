import type {
  Consent,
  Employee,
  History,
  ManagedEmployee,
  OutputForm,
  PayrollDetail,
  PayrollSummary,
  ReviewItem,
  Today,
  WorkSession,
  WorkLocation,
  WorkingNowItem,
} from "../types/api";

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
  | "network"
  | "manager_working"
  | "manager_working_empty"
  | "manager_review_pending"
  | "manager_review_close"
  | "manager_review_resolved"
  | "manager_already_handled"
  | "manager_payroll"
  | "manager_payroll_real_phone"
  | "manager_payroll_a_detail"
  | "manager_session_edit"
  | "manager_payroll_confirm"
  | "manager_payroll_done"
  | "manager_payroll_empty"
  | "manager_employees"
  | "manager_employee_add"
  | "manager_employee_detail"
  | "manager_employee_assign"
  | "manager_employee_assign_open"
  | "manager_locations"
  | "manager_locations_in_use"
  | "manager_lock_open"
  | "manager_messages"
  | "director_report_day"
  | "director_report_week"
  | "director_report_month"
  | "director_report_filtered"
  | "director_report_employees"
  | "director_report_empty"
  | "director_review"
  | "director_payroll"
  | "director_payroll_detail"
  | "director_messages";

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
  {key: "manager_working", label: "QL: Đang làm"},
  {key: "manager_working_empty", label: "QL: Đang làm trống"},
  {key: "manager_review_pending", label: "QL: Cần xử lý"},
  {key: "manager_review_close", label: "QL: Xử lý phiên quên"},
  {key: "manager_review_resolved", label: "QL: Đã xử lý"},
  {key: "manager_already_handled", label: "QL: Đã xử lý bởi người khác"},
  {key: "manager_payroll", label: "QL: Duyệt lương"},
  {key: "manager_payroll_real_phone", label: "QL: Dữ liệu thật GPS"},
  {key: "manager_payroll_a_detail", label: "QL: Chi tiết lương A"},
  {key: "manager_session_edit", label: "QL: Sửa phiên"},
  {key: "manager_payroll_confirm", label: "QL: Hộp xác nhận"},
  {key: "manager_payroll_done", label: "QL: Tổng kết duyệt"},
  {key: "manager_payroll_empty", label: "QL: Không có dữ liệu"},
  {key: "manager_employees", label: "QL: Nhân viên"},
  {key: "manager_employee_add", label: "QL: Thêm nhân viên"},
  {key: "manager_employee_detail", label: "QL: Chi tiết + đơn giá"},
  {key: "manager_employee_assign", label: "QL: Đổi kho"},
  {key: "manager_employee_assign_open", label: "QL: Đổi kho khi đang trong ca"},
  {key: "manager_locations", label: "QL: Kho"},
  {key: "manager_locations_in_use", label: "QL: Kho bị chặn ngừng dùng"},
  {key: "manager_lock_open", label: "QL: Khóa đang trong ca"},
  {key: "manager_messages", label: "QL: Tin nhắn"},
  {key: "director_report_day", label: "GĐ: Báo cáo ngày"},
  {key: "director_report_week", label: "GĐ: Báo cáo tuần"},
  {key: "director_report_month", label: "GĐ: Báo cáo tháng"},
  {key: "director_report_filtered", label: "GĐ: Đang lọc nhân viên"},
  {key: "director_report_employees", label: "GĐ: Chọn nhân viên"},
  {key: "director_report_empty", label: "GĐ: Báo cáo trống"},
  {key: "director_review", label: "GĐ: Cần xử lý"},
  {key: "director_payroll", label: "GĐ: Duyệt lương"},
  {key: "director_payroll_detail", label: "GĐ: Chi tiết lương"},
  {key: "director_messages", label: "GĐ: Tin nhắn"},
];

export const mockEmployee: Employee = {
  id: 1,
  code: "NV001",
  full_name: "Nguyễn Văn A",
  role: "employee",
  tabs: ["attendance", "outputs", "history"],
  has_location_consent: true,
};

export const mockManager: Employee = {
  id: 10,
  code: "QL001",
  full_name: "Quản lý CRV",
  role: "manager",
  tabs: ["working", "review", "payroll", "employees", "messages"],
  has_location_consent: true,
};

export const mockDirector: Employee = {
  id: 11,
  code: "GD001",
  full_name: "Giám đốc CRV",
  role: "director",
  tabs: ["reports", "review", "payroll", "messages"],
  has_location_consent: true,
};

export const mockReportEmployees = [
  {id: 1, code: "NV001", full_name: "Nguyễn Văn A", is_active: true},
  {id: 2, code: "NV002", full_name: "Lê Thị B", is_active: true},
  {id: 3, code: "NV003", full_name: "Trần Văn C", is_active: true},
  {id: 4, code: "NV004", full_name: "Phạm Thị D", is_active: true},
];

export const mockReportProducts = [
  {code: "BOT", name: "Bột", bags: 320, kg: 384},
  {code: "XUC_XICH", name: "Xúc xích", bags: 180, kg: 180},
  {code: "PHO_MAI", name: "Phô mai", bags: 140, kg: 140},
  {code: "CHA_BONG", name: "Chà bông", bags: 120, kg: 120},
  {code: "SOT_CAM", name: "Sốt cam", bags: 90, kg: 180},
  {code: "SOT_TRANG", name: "Sốt trắng", bags: 80, kg: 160},
  {code: "BO", name: "Bơ", bags: 60, kg: 120},
];

export const mockReportSeries = [
  {date: "2026-09-21", minutes: 0, salary: 0, paid: 0, pending: 0, pending_eligible: 0, pending_blocked: 0, needs_review_count: 0, bags: 0, kg: 0},
  {date: "2026-09-22", minutes: 510, salary: 420000, paid: 420000, pending: 0, pending_eligible: 0, pending_blocked: 0, needs_review_count: 0, bags: 180, kg: 240},
  {date: "2026-09-23", minutes: 465, salary: 378000, paid: 250000, pending: 128000, pending_eligible: 100000, pending_blocked: 28000, needs_review_count: 1, bags: 140, kg: 190},
  {date: "2026-09-24", minutes: 540, salary: 448000, paid: 448000, pending: 0, pending_eligible: 0, pending_blocked: 0, needs_review_count: 0, bags: 210, kg: 280},
  {date: "2026-09-25", minutes: 495, salary: 410000, paid: 300000, pending: 110000, pending_eligible: 80000, pending_blocked: 30000, needs_review_count: 1, bags: 180, kg: 234},
  {date: "2026-09-26", minutes: 0, salary: 0, paid: 0, pending: 0, pending_eligible: 0, pending_blocked: 0, needs_review_count: 0, bags: 0, kg: 0},
  {date: "2026-09-27", minutes: 0, salary: 0, paid: 0, pending: 0, pending_eligible: 0, pending_blocked: 0, needs_review_count: 0, bags: 0, kg: 0},
];

export const mockReportSummary = {
  from: "2026-09-21", to: "2026-09-27", minutes: 2490,
  salary: {paid: 1698000, pending: 350000, pending_eligible: 180000, pending_blocked: 170000, needs_review_count: 2, total: 2048000},
  paid: 1698000, pending: 350000, pending_eligible: 180000, pending_blocked: 170000, needs_review_count: 2, total: 2048000, bags: 990, kg: 1284,
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
  location_code: "KHO01",
  location_name: "Xưởng chính",
  location_code_snapshot: "KHO01",
  location_name_snapshot: "Xưởng chính",
};

export const closedSession: WorkSession = {
  ...openSession,
  id: 102,
  check_out_at: "2024-04-24T11:35:00+07:00",
  minutes: 323,
  amount_raw: 161500,
  status: "closed",
};

export const afternoonSession: WorkSession = {
  ...closedSession,
  id: 103,
  check_in_at: "2024-04-24T13:05:00+07:00",
  check_out_at: "2024-04-24T17:10:00+07:00",
  minutes: 245,
  amount_raw: 122500,
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
  const meta = {server_now: "2024-04-24T09:40:15+07:00", checkin_cutoff: "18:00", can_check_in: scenario !== "after_cutoff"};
  if (scenario === "open" || scenario === "locating") {
    return {open_session: openSession, estimated_day_amount: 104000, paid_today: 0, ...meta};
  }
  if (scenario === "open_far") {
    return {open_session: {...openSession, flags: ["gps_out_of_range"], flag_source: "check_in", check_in_distance_m: 250, location_code_snapshot: "KHONHAP", location_name_snapshot: "Kho Nhập", nearby_location_code: "KHODONGGOI", nearby_location_name: "Kho Đóng gói thành phẩm", nearby_location_distance_m: 18}, estimated_day_amount: 68000, paid_today: 0, ...meta};
  }
  return {open_session: null, estimated_day_amount: 0, paid_today: 0, ...meta};
}

export function outputForScenario(scenario: MockScenario, sessionId = 102): OutputForm {
  return {
    session_id: sessionId,
    locked: scenario === "output_locked",
    seconds_remaining: scenario === "output_locked" ? 0 : 572,
    locked_at: scenario === "output_locked" ? "2024-04-24T11:45:00+07:00" : new Date(Date.now() + 572000).toISOString(),
    server_now: scenario === "output_locked" ? "2024-04-24T11:46:00+07:00" : new Date().toISOString(),
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
      paid_amount: 162000,
      pending_amount: 122000,
      blocked_amount: 0,
      batches: [
        {id: 1, batch_no: 1, amount: 162000, approved_at: "2024-04-24T12:00:00+07:00", sessions: [{...closedSession, output: [] as const, pay_batch_id: 1, pending_reason: null, output_locked: true, output_locked_at: "2024-04-24T11:45:00+07:00"}]},
      ],
      unpaid_sessions: [
        {
          ...closedSession,
          id: 103,
          check_in_at: "2024-04-24T13:05:00+07:00",
          check_out_at: "2024-04-24T17:10:00+07:00",
          minutes: 245,
          amount_raw: 122500,
          flags: ["gps_out_of_range"],
          flag_source: "check_in",
          check_in_distance_m: 474,
          location_code_snapshot: "KHONHAP",
          location_name_snapshot: "Kho Nhập",
          nearby_location_code: "KHODONGGOI",
          nearby_location_name: "Kho Đóng gói thành phẩm",
          nearby_location_distance_m: 19,
          pay_batch_id: null,
          pending_reason: "cho_duyet",
          output_locked: false,
          output_locked_at: "2024-04-24T17:20:00+07:00",
          output: mockProducts.map((item) => ({code: item.code, name: item.name, bags: item.bags, kg: item.bags * item.kg_per_bag})),
        },
      ],
    },
    {
      date: "2024-04-23",
      total_amount: 248000,
      paid_amount: 248000,
      pending_amount: 0,
      blocked_amount: 0,
      batches: [
        {id: 2, batch_no: 1, amount: 248000, approved_at: "2024-04-23T18:00:00+07:00", sessions: []},
      ],
      unpaid_sessions: [],
    },
  ],
};

export const mockWorkingNow: WorkingNowItem[] = [
  {session_id: 101, employee_id: 1, code: "NV001", full_name: "Nguyễn Văn A", check_in_at: "2024-04-24T06:12:00+07:00", minutes_worked: 208, flags: [], check_in_distance_m: 12, check_in_accuracy_m: 15, is_outside: false, server_now: "2024-04-24T09:40:15+07:00"},
  {session_id: 201, employee_id: 2, code: "NV002", full_name: "Lê Thị B", check_in_at: "2024-04-24T07:55:00+07:00", minutes_worked: 125, flags: [], check_in_distance_m: 22, check_in_accuracy_m: 20, is_outside: false, server_now: "2024-04-24T09:40:15+07:00"},
  {session_id: 301, employee_id: 3, code: "NV003", full_name: "Trần Văn C", check_in_at: "2024-04-24T08:10:00+07:00", minutes_worked: 45, flags: ["gps_out_of_range"], flag_source: "check_in", check_in_distance_m: 150, check_in_accuracy_m: 35, is_outside: true, server_now: "2024-04-24T09:40:15+07:00"},
  {session_id: 401, employee_id: 4, code: "NV004", full_name: "Phạm Thị D", check_in_at: "2024-04-24T09:20:00+07:00", minutes_worked: 45, flags: [], check_in_distance_m: 14, check_in_accuracy_m: 18, is_outside: false, server_now: "2024-04-24T09:40:15+07:00"},
];

export const mockLocations: WorkLocation[] = [
  {id: 1, code: "KHO01", name: "Kho A", location_type: "workshop", address: null, latitude: 10, longitude: 106, radius_m: 100, coordinate_source: "manual_coordinates", location_accuracy_m: null, is_active: true, current_employee_count: 2, current_employees: [{id: 1, code: "NV001", full_name: "Nguyễn Văn A"}, {id: 3, code: "NV003", full_name: "Trần Văn C"}]},
  {id: 2, code: "KHO02", name: "Kho B", location_type: "workshop", address: null, latitude: 10.0004, longitude: 106, radius_m: 100, coordinate_source: "device_gps", location_accuracy_m: 24, is_active: true, current_employee_count: 2, current_employees: [{id: 2, code: "NV002", full_name: "Lê Thị B"}, {id: 4, code: "NV004", full_name: "Phạm Thị D"}]},
  {id: 3, code: "KHO03", name: "Kho tạm ngừng", location_type: "workshop", address: null, latitude: 10.002, longitude: 106, radius_m: 80, coordinate_source: "device_gps", location_accuracy_m: 126, is_active: false, current_employee_count: 0, current_employees: []},
];

export const mockReviewPending: ReviewItem[] = [
  {...closedSession, id: 501, employee_code: "NV001", employee_name: "Nguyễn Văn A", flags: ["gps_out_of_range"], flag_source: "check_out", check_in_distance_m: 9, check_out_distance_m: 230, check_in_accuracy_m: 20, check_out_accuracy_m: 25},
  {...openSession, id: 502, employee_id: 2, employee_code: "NV002", employee_name: "Lê Thị B", status: "needs_review", review_reason: "forgot_checkout", check_in_at: "2024-04-24T08:05:00+07:00", check_out_at: null, minutes: null, amount_raw: null},
  {...openSession, id: 503, employee_id: 3, employee_code: "NV003", employee_name: "Trần Văn C", status: "needs_review", review_reason: "forgot_checkout", check_in_at: "2024-04-24T13:10:00+07:00", check_out_at: null, minutes: null, amount_raw: null},
];

export const mockReviewResolved: ReviewItem[] = [
  {...closedSession, id: 504, employee_code: "NV001", employee_name: "Nguyễn Văn A", flags: ["gps_out_of_range"], resolved_by_name: "Quản lý CRV", resolved_at: "2024-04-24T10:30:00+07:00", resolved_action: "flags_reviewed", reason: null},
  {...closedSession, id: 505, employee_code: "NV002", employee_name: "Lê Thị B", status: "closed", review_reason: "forgot_checkout", resolved_by_name: "Giám đốc", resolved_at: "2024-04-24T19:05:00+07:00", resolved_action: "session_closed", reason: "Nhân viên quên bấm ra ca"},
];

export const mockPayroll: PayrollSummary[] = [
  {employee_id: 1, code: "NV001", full_name: "Nguyễn Văn A", work_date: "2024-04-24", hourly_rate: null, rate_snapshots: [30000, 40000], rate_count: 2, closed_minutes: 568, eligible_minutes: 245, eligible_session_ids: [103], paid_amount: 162000, day_total_rounded: 284000, pending_amount: 122000, blocked_amount: 0, can_approve: true, unreviewed_flag_session_ids: [], has_open_session: true, has_sessions: true, needs_review_session_ids: [], pending_reason: "open_session", pending_reasons: ["open_session"]},
  {employee_id: 2, code: "NV002", full_name: "Lê Thị B", work_date: "2024-04-24", hourly_rate: 28000, rate_snapshots: [28000], rate_count: 1, closed_minutes: 480, eligible_minutes: 480, eligible_session_ids: [202], paid_amount: 0, day_total_rounded: 224000, pending_amount: 224000, blocked_amount: 0, can_approve: true, unreviewed_flag_session_ids: [], has_open_session: false, has_sessions: true, needs_review_session_ids: [], pending_reason: null, pending_reasons: []},
  {employee_id: 3, code: "NV003", full_name: "Trần Văn C", work_date: "2024-04-24", hourly_rate: 30000, rate_snapshots: [30000], rate_count: 1, closed_minutes: 420, eligible_minutes: 0, eligible_session_ids: [], paid_amount: 210000, day_total_rounded: 210000, pending_amount: 0, blocked_amount: 0, can_approve: false, unreviewed_flag_session_ids: [], has_open_session: false, has_sessions: true, needs_review_session_ids: [], pending_reason: null, pending_reasons: []},
  {employee_id: 4, code: "NV004", full_name: "Phạm Thị D", work_date: "2024-04-24", hourly_rate: 28000, rate_snapshots: [28000], rate_count: 1, closed_minutes: 360, eligible_minutes: 360, eligible_session_ids: [402], paid_amount: 0, day_total_rounded: 168000, pending_amount: 168000, blocked_amount: 0, can_approve: true, unreviewed_flag_session_ids: [], has_open_session: false, has_sessions: true, needs_review_session_ids: [], pending_reason: null, pending_reasons: []},
];

export const mockPayrollRealPhone: PayrollSummary[] = [
  {employee_id: 1, code: "NV001", full_name: "Nguyễn Văn A", work_date: "2024-04-24", hourly_rate: 30000, closed_minutes: 120, eligible_minutes: 0, eligible_session_ids: [], paid_amount: 0, day_total_rounded: 60000, pending_amount: 0, blocked_amount: 60000, can_approve: false, unreviewed_flag_session_ids: [801, 802], has_open_session: true, has_sessions: true, needs_review_session_ids: [], pending_reason: "unreviewed_gps", pending_reasons: ["unreviewed_gps", "open_session"]},
  {employee_id: 2, code: "NV002", full_name: "Lê Thị B", work_date: "2024-04-24", hourly_rate: 28000, closed_minutes: 0, eligible_minutes: 0, eligible_session_ids: [], paid_amount: 0, day_total_rounded: 0, pending_amount: 0, blocked_amount: 0, can_approve: false, unreviewed_flag_session_ids: [], has_open_session: false, has_sessions: false, needs_review_session_ids: [], pending_reason: null, pending_reasons: []},
  ...mockPayroll.filter((row) => row.employee_id !== 1 && row.employee_id !== 2),
];

export const mockPayrollADetail: PayrollDetail = {
  ...mockPayroll[0],
  sessions: [
    {...closedSession, pay_batch_id: 1, is_locked: true},
    {...afternoonSession, pay_batch_id: null, is_locked: false},
    {...openSession, id: 104, check_in_at: "2024-04-24T17:20:00+07:00", pay_batch_id: null, is_locked: false},
  ],
  batches: [{id: 1, batch_no: 1, amount: 162000, approved_by: 10, approved_at: "2024-04-24T12:00:00+07:00"}],
};

export const mockEmployees: ManagedEmployee[] = [
  {id: 1, code: "NV001", full_name: "Nguyễn Văn A", role: "employee", telegram_id: 1001, is_active: true, tabs: ["attendance", "outputs", "history"], current_hourly_rate: 30000, current_rate_effective_from: "2026-09-27T08:00:00+07:00", pending_rate: {id: 9, hourly_rate: 40000, effective_from: "2026-11-01T00:00:00+07:00"}, is_linked: true, has_open_session: true, current_location: {id: 1, code: "KHO01", name: "Kho A", effective_from: "2026-09-27T08:00:00+07:00"}, work_location: mockLocations[0]},
  {id: 2, code: "NV002", full_name: "Lê Thị B", role: "employee", telegram_id: 1002, is_active: true, tabs: ["attendance", "outputs", "history"], current_hourly_rate: 28000, current_rate_effective_from: "2026-09-20T08:00:00+07:00", is_linked: true, has_open_session: false, current_location: {id: 2, code: "KHO02", name: "Kho B", effective_from: "2026-09-20T08:00:00+07:00"}, work_location: mockLocations[1]},
  {id: 3, code: "NV003", full_name: "Trần Văn C", role: "employee", telegram_id: null, is_active: false, tabs: ["attendance", "outputs", "history"], current_hourly_rate: 30000, is_linked: false, has_open_session: false, current_location: {id: 1, code: "KHO01", name: "Kho A", effective_from: "2026-09-18T08:00:00+07:00"}, work_location: mockLocations[0]},
  {id: 4, code: "NV004", full_name: "Phạm Thị D", role: "employee", telegram_id: 1004, is_active: true, tabs: ["attendance", "outputs", "history"], current_hourly_rate: 28000, current_rate_effective_from: "2026-09-20T08:00:00+07:00", is_linked: true, has_open_session: false, current_location: {id: 2, code: "KHO02", name: "Kho B", effective_from: "2026-09-24T08:00:00+07:00"}, work_location: mockLocations[1]},
];

export const mockEmployeeLocationHistory = [
  {id: 11, employee_id: 1, location_id: 1, location_code: "KHO01", location_name: "Kho A", effective_from: "2026-09-27T08:00:00+07:00", effective_to: null, changed_by: 10, changed_by_name: "Quản lý CRV", reason: "Điều chuyển về xưởng chính"},
  {id: 10, employee_id: 1, location_id: 2, location_code: "KHO02", location_name: "Kho B", effective_from: "2026-09-20T08:00:00+07:00", effective_to: "2026-09-27T08:00:00+07:00", changed_by: 10, changed_by_name: "Quản lý CRV", reason: "Hỗ trợ kho đóng gói"},
];
