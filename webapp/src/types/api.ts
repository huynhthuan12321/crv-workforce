export type Role = "employee" | "manager" | "director";

export type TabKey =
  | "attendance"
  | "outputs"
  | "history"
  | "working"
  | "review"
  | "payroll"
  | "employees"
  | "reports";

export type Employee = {
  id: number;
  code: string;
  full_name: string;
  role: Role;
  telegram_id?: number | null;
  is_active?: boolean | null;
  tabs: TabKey[];
  has_location_consent?: boolean;
};

export type WorkSessionStatus = "open" | "closed" | "needs_review";

export type WorkSession = {
  id: number;
  employee_id: number;
  work_date: string;
  check_in_at: string;
  check_out_at: string | null;
  minutes: number | null;
  rate_snapshot: number;
  amount_raw: number | null;
  status: WorkSessionStatus;
  review_reason?: string | null;
  flags: string[];
  flag_source?: "check_in" | "check_out" | "both" | string | null;
  check_in_accuracy_m?: number | null;
  check_in_distance_m: number;
  check_out_accuracy_m?: number | null;
  check_out_distance_m: number | null;
};

export type Today = {
  open_session: WorkSession | null;
  estimated_day_amount: number;
  paid_today: number;
  server_now: string;
  checkin_cutoff: string;
  can_check_in: boolean;
};

export type Consent = {
  version: number;
  content: string;
  effective_at: string;
  accepted: boolean;
} | null;

export type ProductTotal = {
  code: string;
  name: string;
  bags: number;
  kg: number;
};

export type OutputItem = {
  code: string;
  name: string;
  kg_per_bag: number;
  bags: number;
};

export type OutputForm = {
  session_id: number;
  locked: boolean;
  seconds_remaining: number;
  locked_at: string;
  server_now: string;
  items: OutputItem[];
};

export type OutputSubmit = {
  session_id: number;
  total_kg: number;
  locked_at: string | null;
};

export type HistorySession = WorkSession & {
  pay_batch_id: number | null;
  pending_reason: string | null;
  output_locked?: boolean;
  output_locked_at?: string | null;
  output: ProductTotal[];
};

export type HistoryBatch = {
  id: number;
  batch_no: number;
  amount: number;
  approved_at: string;
  sessions: HistorySession[];
};

export type HistoryDay = {
  date: string;
  total_amount: number;
  paid_amount: number;
  pending_amount: number;
  blocked_amount: number;
  batches: HistoryBatch[];
  unpaid_sessions: HistorySession[];
};

export type History = {
  from: string;
  to: string;
  days: HistoryDay[];
};

export type LocationPayload = {
  lat: number;
  lng: number;
  accuracy_m: number;
};

export type AuthData = {
  token: string;
  employee: Employee;
};

export type WorkingNowItem = {
  session_id: number;
  employee_id: number;
  code: string;
  full_name: string;
  check_in_at: string;
  minutes_worked: number;
  flags: string[];
  flag_source?: "check_in" | "check_out" | "both" | string | null;
  check_in_distance_m: number | null;
  check_in_accuracy_m: number | null;
  check_out_distance_m?: number | null;
  check_out_accuracy_m?: number | null;
  is_outside: boolean;
  server_now: string;
};

export type ReviewItem = WorkSession & {
  employee_code: string;
  employee_name: string;
  resolved_by?: number | null;
  resolved_by_name?: string | null;
  resolved_at?: string | null;
  resolved_action?: "flags_reviewed" | "session_closed";
  reason?: string | null;
};

export type PayrollSummary = {
  employee_id: number;
  code: string;
  full_name: string;
  work_date: string;
  hourly_rate: number | null;
  closed_minutes: number;
  eligible_minutes: number;
  eligible_session_ids: number[];
  paid_amount: number;
  day_total_rounded: number;
  pending_amount: number;
  blocked_amount: number;
  can_approve: boolean;
  unreviewed_flag_session_ids: number[];
  has_open_session: boolean;
  has_sessions: boolean;
  needs_review_session_ids: number[];
  pending_reason: "open_session" | "unreviewed_gps" | "forgot_checkout" | null;
  pending_reasons: Array<"open_session" | "unreviewed_gps" | "forgot_checkout" | string>;
};

export type PayrollSession = WorkSession & {
  pay_batch_id: number | null;
  is_locked: boolean;
};

export type PayrollBatch = {
  id: number;
  batch_no: number;
  amount: number;
  approved_by: number;
  approved_at: string;
};

export type PayrollDetail = PayrollSummary & {
  sessions: PayrollSession[];
  batches: PayrollBatch[];
};

export type PayrollApproveResult = {
  employee_id: number;
  batch_id: number;
  batch_no: number;
  amount: number;
};

export type ManagedEmployee = Employee & {
  current_hourly_rate: number | null;
  is_linked: boolean;
  has_open_session: boolean;
  invite_url?: string | null;
};

export type RateHistory = {
  id: number;
  hourly_rate: number;
  effective_from: string;
};

export type ReportEmployee = {
  id: number;
  code: string;
  full_name: string;
  is_active: boolean;
};

export type ReportSummary = {
  from: string;
  to: string;
  minutes: number;
  salary: {paid: number; pending: number; pending_eligible: number; pending_blocked: number; needs_review_count: number; total: number};
  paid: number;
  pending: number;
  pending_eligible: number;
  pending_blocked: number;
  needs_review_count: number;
  total: number;
  bags: number;
  kg: number;
};

export type ReportTimeseries = {
  date: string;
  minutes: number;
  salary: number;
  paid: number;
  pending: number;
  pending_eligible: number;
  pending_blocked: number;
  needs_review_count: number;
  bags: number;
  kg: number;
};
