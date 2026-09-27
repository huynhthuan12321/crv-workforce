export class ApiError extends Error {
  code: string;
  status?: number;
  details?: Record<string, unknown>;

  constructor(code: string, message: string, status?: number, details?: Record<string, unknown>) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}
