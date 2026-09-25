/** Error codes the client adds on top of the contract's error codes (Appendix A1). */
export type ClientErrorCode = "network_error" | "bad_response" | "not_in_mock";

export interface ApiErrorInit {
  status: number;
  code: string;
  message: string;
  url: string;
  /** For not_in_mock: issue dates that do have a demo file for this endpoint. */
  mockDates?: string[];
}

/** Every failed request becomes an ApiError, whatever the source (API, mock, snapshot). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly url: string;
  readonly mockDates: string[];

  constructor(init: ApiErrorInit) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.url = init.url;
    this.mockDates = init.mockDates ?? [];
  }

  /** Builds an ApiError from a response body in the contract error shape, if it is one. */
  static fromBody(status: number, url: string, body: unknown): ApiError {
    const err = (body as { error?: { code?: unknown; message?: unknown } } | null)?.error;
    return new ApiError({
      status,
      url,
      code: typeof err?.code === "string" ? err.code : `http_${status}`,
      message: typeof err?.message === "string" ? err.message : `Request failed with ${status}`,
    });
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}
