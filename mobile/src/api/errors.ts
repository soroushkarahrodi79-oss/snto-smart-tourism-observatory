export type ApiErrorKind =
  | 'timeout'
  | 'network'
  | 'unauthorized'
  | 'forbidden'
  | 'not_found'
  | 'server'
  | 'invalid_response';

export class ApiError extends Error {
  constructor(
    public readonly kind: ApiErrorKind,
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
