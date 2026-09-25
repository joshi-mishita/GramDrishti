/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_REAL_ENDPOINTS?: string;
  readonly VITE_SNAPSHOT?: string;
  readonly VITE_DEFAULT_ISSUE_DATE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
