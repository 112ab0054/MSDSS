<?php
declare(strict_types=1);
require '/app/vendor/autoload.php';
$app = require '/app/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
if (config('database.connections.mysql.host') !== 'db' || config('database.connections.mysql.database') !== 'msdss_bagisto') {
    throw new RuntimeException('Refusing non-isolated database');
}
$channel = core()->getDefaultChannel();
if (!$channel) { throw new RuntimeException('Default channel missing'); }
$channel->hostname = '127.0.0.1';
$channel->save();
foreach (['customer.settings.email.verification' => '0', 'sales.carriers.flatrate.active' => '1',
          'sales.carriers.flatrate.default_rate' => '5', 'sales.payment_methods.cashondelivery.active' => '1',
          'sales.payment_methods.moneytransfer.active' => '1'] as $code => $value) {
    Illuminate\Support\Facades\DB::table('core_config')->updateOrInsert(
        ['code' => $code, 'channel_code' => $channel->code, 'locale_code' => null], ['value' => $value]);
}
$repo = app(Webkul\Product\Repositories\ProductRepository::class);
$inventory = $channel->inventory_sources()->first();
if (!$inventory) { throw new RuntimeException('Channel inventory source missing'); }
foreach (['MSDSS-PHASE1-SIMPLE' => 'MSDSS Phase One Product', 'MSDSS-PHASE1-SUPPORT' => 'MSDSS Support Product'] as $sku => $name) {
$product = $repo->findOneByField('sku', $sku);
if (!$product) {
    $family = Illuminate\Support\Facades\DB::table('attribute_families')->where('code', 'default')->first();
    if (!$family) { throw new RuntimeException('Default attribute family missing'); }
    $product = $repo->create(['type' => 'simple', 'attribute_family_id' => $family->id, 'sku' => $sku]);
}
$repo->update(['channel' => $channel->code, 'locale' => $channel->default_locale->code,
    'sku' => $product->sku, 'name' => $name, 'url_key' => strtolower($sku),
    'short_description' => 'Local normal-shopping verification product',
    'description' => 'Local normal-shopping verification product', 'price' => 25,
    'weight' => 1, 'status' => 1, 'visible_individually' => 1, 'guest_checkout' => 1,
    'tax_category_id' => null, 'inventories' => [$inventory->id => 100],
    'channels' => [$channel->id], 'categories' => [$channel->root_category_id]], $product->id);
}
$key = Webkul\BagistoApi\Models\StorefrontKey::firstOrCreate(['name' => 'MSDSS phase one local'],
    ['key' => Webkul\BagistoApi\Models\StorefrontKey::generateKey(), 'is_active' => true, 'rate_limit' => 100]);
$admin = Webkul\User\Models\Admin::first();
$password = bin2hex(random_bytes(24));
if ($admin) {
    $admin->password = Illuminate\Support\Facades\Hash::make($password);
    $admin->save();
}
echo json_encode(['storefront_key' => $key->key, 'channel' => $channel->code,
    'locale' => $channel->default_locale->code, 'currency' => $channel->base_currency->code,
    'admin_email' => $admin?->email, 'admin_password' => $password], JSON_THROW_ON_ERROR);
