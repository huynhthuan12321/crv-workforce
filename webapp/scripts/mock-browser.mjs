import {existsSync} from "node:fs";

export const chromeCandidates = [
  process.env.CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
].filter(Boolean);

export const chromePath = chromeCandidates.find((path) => existsSync(path));

export const baseUrl = process.env.CRV_MOCK_URL || "http://127.0.0.1:4175";

export const scenarios = [
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
