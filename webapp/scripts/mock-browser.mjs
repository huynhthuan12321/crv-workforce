import {existsSync} from "node:fs";

export const chromeCandidates = [
  process.env.CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
].filter(Boolean);

export const chromePath = chromeCandidates.find((path) => existsSync(path));

export const baseUrl = process.env.CRV_MOCK_URL || "http://127.0.0.1:4175";

export const employeeScenarios = [
  ["idle", "attendance", "01_cham_cong_chua_vao_ca"],
  ["locating", "attendance", "02_dang_lay_vi_tri"],
  ["open", "attendance", "03_trong_ca"],
  ["open_far", "attendance", "04_gps_ngoai_250m"],
  ["after_cutoff", "attendance", "05_sau_18h"],
  ["output_editable", "outputs", "06_san_luong_con_10_phut"],
  ["output_locked", "outputs", "07_san_luong_da_khoa"],
  ["history_multi", "history", "08_lich_su_nhieu_dot"],
  ["consent", "attendance", "09_chua_dong_y_vi_tri"],
  ["not_registered", "attendance", "10_chua_duoc_cap_quyen"],
  ["locked", "attendance", "11_bi_khoa"],
  ["expired", "attendance", "12_het_phien"],
  ["network", "attendance", "13_loi_mang"],
];

export const managerScenarios = [
  ["manager_working", "working", "01_dang_lam"],
  ["manager_working_empty", "working", "02_dang_lam_trong"],
  ["manager_review_pending", "review", "03_can_xu_ly"],
  ["manager_review_resolved", "review", "04_da_xu_ly"],
  ["manager_already_handled", "review", "05_already_handled"],
  ["manager_payroll", "payroll", "06_duyet_luong"],
  ["manager_payroll_a_detail", "payroll", "07_chi_tiet_luong_a"],
  ["manager_session_edit", "payroll", "08_sua_phien"],
  ["manager_payroll_confirm", "payroll", "09_hop_xac_nhan"],
  ["manager_payroll_done", "payroll", "10_tong_ket_duyet"],
  ["manager_payroll_empty", "payroll", "11_khong_co_du_lieu"],
  ["manager_employees", "employees", "12_danh_sach_nhan_vien"],
  ["manager_employee_add", "employees", "13_them_nhan_vien"],
  ["manager_employee_detail", "employees", "14_chi_tiet_don_gia"],
  ["manager_lock_open", "employees", "15_khoa_dang_trong_ca"],
];

export const scenarios = [...employeeScenarios, ...managerScenarios];
