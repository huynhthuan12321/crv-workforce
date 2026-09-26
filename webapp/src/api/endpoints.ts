import { api } from "./client";
import type { ApiResponse, User } from "../types";

export const authApi = {
  validate: () => api.post<ApiResponse<User>>("/auth/validate")
};

export const usersApi = {
  getMe: () => api.get<ApiResponse<User>>("/users/me"),
  updateMe: (data: { bio?: string; language_code?: string }) =>
    api.patch<ApiResponse<User>>("/users/me", data),
  getUser: (telegramId: number) =>
    api.get<ApiResponse<User>>(`/users/${telegramId}`)
};
