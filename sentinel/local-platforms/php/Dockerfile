FROM composer:2.8.12@sha256:5248900ab8b5f7f880c2d62180e40960cd87f60149ec9a1abfd62ac72a02577c AS composer
FROM php:8.3.30-cli-bookworm@sha256:68e9d207ef1afe71769cbcf17fd671c7f565ad1cad8bdfb02c710eb84da50da1
RUN apt-get update && apt-get install -y --no-install-recommends \
    git unzip libicu-dev libzip-dev libpng-dev libjpeg62-turbo-dev \
    libfreetype6-dev libxml2-dev libxslt1-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j2 bcmath calendar exif gd intl pdo_mysql zip xsl opcache \
    && rm -rf /var/lib/apt/lists/*
COPY --from=composer /usr/bin/composer /usr/local/bin/composer
RUN printf 'memory_limit=512M\nmax_execution_time=120\n' > /usr/local/etc/php/conf.d/msdss.ini
WORKDIR /app
ENV COMPOSER_ALLOW_SUPERUSER=1
