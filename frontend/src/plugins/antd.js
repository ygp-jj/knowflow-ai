/**
 * 功能：按需注册当前管理台页面使用到的 Ant Design Vue 组件，避免全量插件注册。
 */
import {
  Button,
  Card,
  Drawer,
  Empty,
  Form,
  Input,
  Layout,
  Menu,
  Modal,
  Select,
  Skeleton,
  Space,
  Table,
  Tag,
  Upload,
} from 'ant-design-vue';

/** 当前项目实际使用的组件列表。 */
const USED_ANTD_COMPONENTS = [
  Button,
  Tag,
  Menu,
  Menu.Item,
  Layout,
  Layout.Sider,
  Layout.Header,
  Layout.Content,
  Table,
  Space,
  Card,
  Select,
  Drawer,
  Skeleton,
  Empty,
  Modal,
  Form,
  Form.Item,
  Input,
  Input.TextArea,
  Upload.Dragger,
];

/**
 * 功能：向 Vue 应用实例按需注册 Ant Design Vue 组件。
 * @param {{ component: (name: string, component: any) => any }} app Vue 应用实例。
 * @returns {void}
 */
export function registerAntdComponents(app) {
  USED_ANTD_COMPONENTS.forEach((componentInstance) => {
    app.component(componentInstance.name, componentInstance);
  });
}
