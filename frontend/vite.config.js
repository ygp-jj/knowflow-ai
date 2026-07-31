/**
 * 功能：配置 Vite 构建、路径别名、手动分包和本地开发服务。
 */
import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig(({ mode }) => {
  /** 当前模式下的环境变量。 */
  const env = loadEnv(mode, process.cwd(), '');
  /** 本地开发代理指向的后端地址。优先使用环境变量，默认直接指向云服务器后端。 */
  const proxyTarget = env.VITE_PROXY_TARGET || 'http://120.26.2.20:8000';

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            vue: ['vue', 'vue-router'],
            antd: ['ant-design-vue', '@ant-design/icons-vue'],
            request: ['axios'],
          },
        },
      },
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});