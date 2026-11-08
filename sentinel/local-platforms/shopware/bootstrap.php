<?php
// Run only inside the dedicated msdss-phase1-shopware container.
// stdout contains a credential: the caller must save it privately and never print it.
declare(strict_types=1);
require '/var/www/html/vendor/autoload.php';
(new Symfony\Component\Dotenv\Dotenv())->usePutenv()->loadEnv('/var/www/html/.env');
$url = parse_url($_SERVER['DATABASE_URL'] ?? getenv('DATABASE_URL'));
if (!$url || !isset($url['host'], $url['path'])) {
    throw new RuntimeException('Local database configuration unavailable');
}
$pdo = new PDO('mysql:host='.$url['host'].';port='.($url['port'] ?? 3306).';dbname='.ltrim($url['path'], '/').';charset=utf8mb4',
    urldecode($url['user'] ?? ''), urldecode($url['pass'] ?? ''), [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$query = $pdo->prepare('SELECT LOWER(HEX(id)) AS id, access_key FROM sales_channel WHERE active = 1 AND type_id = UNHEX(?) LIMIT 1');
$query->execute([Shopware\Core\Defaults::SALES_CHANNEL_TYPE_STOREFRONT]);
$channel = $query->fetch(PDO::FETCH_ASSOC);
if (!$channel) { throw new RuntimeException('No active local storefront channel'); }
$pdo->beginTransaction();
$query = $pdo->prepare('SELECT LOWER(HEX(id)) FROM sales_channel_domain WHERE sales_channel_id = UNHEX(?) LIMIT 1');
$query->execute([$channel['id']]);
$domain = $query->fetchColumn();
if (!$domain) { throw new RuntimeException('No local storefront domain'); }
$query = $pdo->prepare('UPDATE sales_channel_domain SET url = ? WHERE id = UNHEX(?)');
$query->execute(['http://127.0.0.1:18082', $domain]);
$key = 'core.loginRegistration.doubleOptInRegistration';
$query = $pdo->prepare('SELECT id FROM system_config WHERE configuration_key = ? AND sales_channel_id = UNHEX(?) LIMIT 1');
$query->execute([$key, $channel['id']]);
$id = $query->fetchColumn();
if ($id) {
    $query = $pdo->prepare('UPDATE system_config SET configuration_value = ?, updated_at = NOW(3) WHERE id = ?');
    $query->execute(['{"_value":false}', $id]);
} else {
    $query = $pdo->prepare('INSERT INTO system_config (id, configuration_key, configuration_value, sales_channel_id, created_at) VALUES (UNHEX(?), ?, ?, UNHEX(?), NOW(3))');
    $query->execute([bin2hex(random_bytes(16)), $key, '{"_value":false}', $channel['id']]);
}
$pdo->commit();
$offline = [];
foreach ($pdo->query('SELECT LOWER(HEX(id)) AS id, handler_identifier FROM payment_method WHERE active = 1')->fetchAll(PDO::FETCH_ASSOC) as $payment) {
    if (in_array($payment['handler_identifier'], [
        'Shopware\\Core\\Checkout\\Payment\\Cart\\PaymentHandler\\InvoicePayment',
        'Shopware\\Core\\Checkout\\Payment\\Cart\\PaymentHandler\\CashPayment',
    ], true)) { $offline[] = $payment['id']; }
}
if (!$offline) { throw new RuntimeException('No native offline payment handler available'); }
echo json_encode(['access_key' => $channel['access_key'], 'channel_id' => $channel['id'],
    'offline_payment_ids' => $offline], JSON_THROW_ON_ERROR);
