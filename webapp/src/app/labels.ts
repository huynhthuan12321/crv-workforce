import type {Role, TabKey} from "../types/api";

export const tabLabels: Record<TabKey, string> = {
  attendance: "Chấm công",
  outputs: "Sản lượng",
  history: "Lịch sử",
  working: "Đang làm",
  review: "Cần xử lý",
  payroll: "Duyệt lương",
  employees: "Quản lý",
  reports: "Báo cáo",
};

export const tabIcons: Record<TabKey, string> = {
  attendance: "●",
  outputs: "▦",
  history: "◷",
  working: "◉",
  review: "!",
  payroll: "₫",
  employees: "◎",
  reports: "▥",
};

export const roleLabels: Record<Role, string> = {
  employee: "Nhân viên",
  manager: "Quản lý",
  director: "Giám đốc",
};

export const errorTitles: Record<string, string> = {
  NOT_REGISTERED: "Chưa được cấp quyền",
  ACCOUNT_LOCKED: "Tài khoản đã bị khóa",
  INITDATA_EXPIRED: "Phiên đăng nhập hết hạn",
  SESSION_EXPIRED: "Phiên đăng nhập hết hạn",
  NETWORK_ERROR: "Lỗi mạng",
};

export const errorMessages: Record<string, string> = {
  NOT_REGISTERED: "Telegram của bạn chưa được liên kết với hồ sơ nhân viên. Vui lòng mở đúng link mời do quản lý cấp.",
  ACCOUNT_LOCKED: "Hồ sơ của bạn đang bị khóa. Vui lòng liên hệ quản lý để được hỗ trợ.",
  INITDATA_EXPIRED: "Vui lòng đóng Mini App và mở lại từ Telegram để lấy phiên đăng nhập mới.",
  SESSION_EXPIRED: "Vui lòng đóng Mini App và mở lại từ Telegram để lấy phiên đăng nhập mới.",
  NETWORK_ERROR: "Không thể kết nối máy chủ. Vui lòng kiểm tra mạng rồi thử lại.",
};
