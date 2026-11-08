<?php
declare(strict_types=1);
$platform = $argv[1] ?? '';
if (!in_array($platform, ['bagisto', 'sylius'], true)
    || getenv('DB_HOST') !== 'db' || getenv('DB_DATABASE') !== 'msdss_'.$platform) {
    throw new RuntimeException('Refusing a non-isolated database');
}
$pdo = new PDO('mysql:host=db;dbname=msdss_'.$platform, getenv('DB_USERNAME'), getenv('DB_PASSWORD'),
    [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$count = (int) $pdo->query('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()')->fetchColumn();
if ($count !== 0) { throw new RuntimeException('Database already contains tables; refusing destructive reinstallation'); }
echo "Isolated empty database verified.\n";
