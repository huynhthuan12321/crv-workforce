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
  flags: string[];
  check_in_distance_m: number;
  check_out_distance_m: number | null;
};

export type Today = {
  open_session: WorkSession | null;
  estimated_day_amount: number;
  paid_today: number;
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
