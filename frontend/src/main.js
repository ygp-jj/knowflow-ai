/**
 * 功能：创建 Vue 应用实例，挂载路由和按需注册的 UI 组件。
 */
import { createApp } from 'vue';
import 'ant-design-vue/dist/reset.css';

import App from './App.vue';
import { registerAntdComponents } from './plugins/antd';
import router from './router';
import './style.css';

/** 应用实例。 */
const app = createApp(App);

app.use(router);
registerAntdComponents(app);
app.mount('#app');
