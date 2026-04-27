/// <reference types="vite/client" />

interface ImportMetaEnv {
  // 使用方式: import.meta.env.VITE_*
  // 当前未定义 VITE_ 环境变量（API 通过 Vite proxy 代理到后端）
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
