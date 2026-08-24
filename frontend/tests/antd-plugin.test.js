/**
 * 功能：验证 Ant Design Vue 组件按需注册列表与当前页面实际依赖一致。
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { registerAntdComponents } from '../src/plugins/antd.js';

test('registerAntdComponents only registers the components used by current pages', () => {
  /** 模拟应用实例。 */
  const fakeApp = {
    registered: [],
    component(name) {
      this.registered.push(name);
      return this;
    },
  };

  registerAntdComponents(fakeApp);

  assert.deepEqual(fakeApp.registered, [
    'AAlert',
    'AButton',
    'ATag',
    'AMenu',
    'AMenuItem',
    'ALayout',
    'ALayoutSider',
    'ALayoutHeader',
    'ALayoutContent',
    'ATable',
    'ASpace',
    'ACard',
    'ASelect',
    'ADrawer',
    'ASkeleton',
    'AEmpty',
    'AModal',
    'AForm',
    'AFormItem',
    'AInput',
    'ATextarea',
    'AInputPassword',
    'AUploadDragger',
    'APagination',
    'ASpin',
  ]);
});
