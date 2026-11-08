<?php
declare(strict_types=1);
if (getenv('DB_HOST') !== 'db' || getenv('DB_DATABASE') !== 'msdss_sylius') {
    throw new RuntimeException('Refusing non-isolated database');
}
$pdo = new PDO('mysql:host=db;dbname=msdss_sylius;charset=utf8mb4', getenv('DB_USERNAME'), getenv('DB_PASSWORD'),
    [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$channel = $pdo->query('SELECT code FROM sylius_channel WHERE enabled = 1 ORDER BY id LIMIT 1')->fetchColumn();
if (!$channel) { throw new RuntimeException('Enabled channel missing'); }
$query = $pdo->prepare('UPDATE sylius_channel SET hostname = ?, account_verification_required = 0 WHERE code = ?');
$query->execute(['127.0.0.1', $channel]);
$codes = $pdo->query("SELECT p.code FROM sylius_payment_method p JOIN sylius_gateway_config g ON g.id = p.gateway_config_id WHERE p.is_enabled = 1 AND g.factory_name = 'offline'")->fetchAll(PDO::FETCH_COLUMN);
if (!$codes) { throw new RuntimeException('No offline payment fixture; refuse to use an external gateway'); }
$country = $pdo->query("SELECT code FROM sylius_country WHERE enabled = 1 ORDER BY (code = 'US') DESC, code LIMIT 1")->fetchColumn();
if (!$country) { throw new RuntimeException('No enabled country fixture'); }
$password = bin2hex(random_bytes(24));
$query = $pdo->prepare('UPDATE sylius_admin_user SET password = ?');
$query->execute([password_hash($password, PASSWORD_BCRYPT)]);
echo json_encode(['channel' => $channel, 'country' => $country, 'offline_payment_codes' => $codes,
    'admin_password' => $password], JSON_THROW_ON_ERROR);
