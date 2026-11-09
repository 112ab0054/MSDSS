/* 僅建立帶 MSDSS 標記的本機測試資料；透過已安裝 Medusa 原生服務／workflow，不寫 SQL。 */
const fs = require('fs');
const { createRequire } = require('module');
const r = createRequire(process.cwd() + '/package.json');
const mr = createRequire(r.resolve('@medusajs/medusa'));
const { Modules, ContainerRegistrationKeys } = mr('@medusajs/framework/utils');
const flows = mr('@medusajs/core-flows');

exports.default = async function ({ container, args }) {
  const input = JSON.parse(fs.readFileSync(args[0], 'utf8'));
  const result = { mode: input.mode, native_platform_operations: true };
  if (input.mode === 'catalog') {
    const product = container.resolve(Modules.PRODUCT);
    const order = container.resolve(Modules.ORDER);
    const suffix = input.run_id;
    result.collection = await product.createProductCollections({ title: 'MSDSS demo collection ' + suffix, handle: 'msdss-demo-' + suffix });
    result.tag = await product.createProductTags({ value: 'MSDSS demo tag ' + suffix });
    result.type = await product.createProductTypes({ value: 'MSDSS demo type ' + suffix });
    result.reason = await order.createReturnReasons({ value: 'msdss-demo-' + suffix, label: 'MSDSS demo wrong size ' + suffix, description: 'Local offline demo return fixture' });
    const { result: promotions } = await flows.createPromotionsWorkflow(container).run({ input: { promotionsData: [{
      code: 'MSDSSDEMO' + suffix.toUpperCase(), type: 'standard', status: 'active', is_automatic: false,
      application_method: { type: 'percentage', target_type: 'items', allocation: 'across', value: 10 }
    }] } });
    result.promotion = promotions[0];
  } else if (input.mode === 'reset') {
    const { http } = container.resolve(ContainerRegistrationKeys.CONFIG_MODULE).projectConfig;
    const { result: token } = await flows.generateResetPasswordTokenWorkflow(container).run({ input: {
      entityId: input.email, actorType: 'customer', provider: 'emailpass', secret: http.jwtSecret, jwtOptions: http.jwtOptions
    } });
    result.token = token;
    result.scope = 'native workflow fixture; not evidence that HTTP reset event was received or email delivered';
  } else if (input.mode === 'verification') {
    const auth = container.resolve(Modules.AUTH);
    const verification = await auth.requestAuthVerification({ auth_identity_id: input.auth_identity_id,
      entity_id: input.email, entity_type: 'email', code_provider: 'token' });
    result.token = verification.code;
    result.entity_id = verification.entity_id;
    result.scope = 'native auth service issued code for own identity; no email delivery claim';
  } else if (input.mode === 'fulfill') {
    const { result: fulfillment } = await flows.createOrderFulfillmentWorkflow(container).run({ input: {
      order_id: input.order_id, items: [{ id: input.item_id, quantity: 1 }], no_notification: true,
      metadata: { msdss_demo: input.run_id }
    } });
    result.fulfillment = fulfillment;
    const q = container.resolve(ContainerRegistrationKeys.QUERY);
    const { data: orders } = await q.graph({ entity: 'order', fields: ['id', 'items.*', 'shipping_methods.*'], filters: { id: input.order_id } });
    result.order = orders[0];
  } else if (input.mode === 'return_shipping') {
    const fulfillment = container.resolve(Modules.FULFILLMENT);
    const options = await fulfillment.listShippingOptions({}, { relations: ['type', 'rules'] });
    const source = options.find(x => x.id === input.shipping_option_id);
    if (!source || source.provider_id !== 'manual_manual') throw new Error('Expected existing local manual provider');
    const { result: optionsCreated } = await flows.createShippingOptionsWorkflow(container).run({ input: [{
      name: 'MSDSS demo return ' + input.run_id, service_zone_id: source.service_zone_id,
      shipping_profile_id: source.shipping_profile_id, provider_id: source.provider_id,
      type: { label: 'MSDSS local return', description: 'Offline demo only', code: 'msdss-return-' + input.run_id },
      data: { id: 'manual-return' }, price_type: 'flat', prices: [{ amount: 0, currency_code: input.currency_code }],
      rules: [{ attribute: 'is_return', operator: 'eq', value: 'true' }, { attribute: 'enabled_in_store', operator: 'eq', value: 'true' }]
    }] });
    result.shipping_option = optionsCreated[0];
  } else throw new Error('Unknown fixture mode');
  // 呼叫端只把完整輸出存入 ignored .runtime；公開紀錄必須經遮蔽。
  console.log('MSDSS_PRIVATE_RESULT=' + JSON.stringify(result));
};
