# Настройка VPS для Discourse

Руководство по настройке сервера Digital Ocean для установки Discourse форума.

## 📋 Требования

### Минимальная конфигурация для 100-200 пользователей

| Параметр | Минимум | Рекомендуется |
|----------|---------|---------------|
| CPU | 2 ядра | 4 ядра |
| RAM | 2 GB | 4 GB |
| Диск | 40 GB SSD | 80 GB SSD |
| Bandwidth | 1 TB/мес | 2 TB/мес |

## 🚀 Создание Droplet на Digital Ocean

### Шаг 1: Регистрация и создание Droplet

1. Зарегистрируйтесь на [DigitalOcean](https://www.digitalocean.com/)
2. Нажмите **Create** → **Droplets**
3. Выберите параметры:

#### Образ (Image)
- **Distribution:** Ubuntu 22.04 LTS x64

#### Plan
- **Basic Plan:** $24/месяц (2 vCPU, 4 GB RAM, 80 GB SSD)
- или **Premium:** $48/месяц (4 vCPU, 8 GB RAM, 160 GB SSD)

#### Datacenter Region
Выберите ближайший к вашим пользователям регион:
- **Европа:** Amsterdam, Frankfurt, London
- **Азия:** Singapore, Bangalore
- **Америка:** New York, San Francisco

#### Authentication
- **SSH Key** (рекомендуется) или
- **Password** (менее безопасно)

#### Hostname
- Например: `fishery-forum`

### Шаг 2: Настройка DNS

1. Добавьте ваш домен в Digital Ocean:
   - Перейдите в **Networking** → **Domains**
   - Добавьте домен

2. Создайте DNS записи:
   - **A Record:** `forum` → IP адрес вашего Droplet
   - **CNAME Record:** `www.forum` → `forum.yourdomain.com`

3. Обновите nameservers у вашего регистратора домена:
   ```
   ns1.digitalocean.com
   ns2.digitalocean.com
   ns3.digitalocean.com
   ```

## 🔧 Начальная настройка сервера

### Подключение к серверу

```bash
ssh root@your_server_ip
```

### Обновление системы

```bash
apt update
apt upgrade -y
```

### Настройка firewall

```bash
# Разрешить SSH
ufw allow OpenSSH

# Разрешить HTTP и HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Включить firewall
ufw enable

# Проверить статус
ufw status
```

### Создание swap файла (если RAM < 4GB)

```bash
# Создать 2GB swap
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Сделать постоянным
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## 📦 Установка Docker

Discourse использует Docker для развертывания.

```bash
# Установить зависимости
apt install -y apt-transport-https ca-certificates curl software-properties-common

# Добавить официальный GPG ключ Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -

# Добавить репозиторий Docker
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# Установить Docker
apt update
apt install -y docker-ce

# Проверить установку
docker --version
```

## 🗣️ Установка Discourse

### Клонирование репозитория Discourse Docker

```bash
# Установить Git
apt install -y git

# Клонировать репозиторий
mkdir -p /var/discourse
git clone https://github.com/discourse/discourse_docker.git /var/discourse
cd /var/discourse
```

### Настройка Discourse

```bash
./discourse-setup
```

Скрипт задаст вам вопросы:

1. **Hostname for your Discourse?**
   ```
   forum.fisherygroup.com
   ```

2. **Email address for admin account?**
   ```
   admin@fisherygroup.com
   ```

3. **SMTP server address?**
   Варианты:
   - **SendGrid:** smtp.sendgrid.net
   - **Mailgun:** smtp.mailgun.org
   - **Gmail:** smtp.gmail.com (не рекомендуется для продакшена)

4. **SMTP port?**
   ```
   587
   ```

5. **SMTP user name?**
   ```
   apikey (для SendGrid) или ваш username
   ```

6. **SMTP password?**
   ```
   ваш API ключ или пароль
   ```

7. **Let's Encrypt account email?**
   ```
   admin@fisherygroup.com
   ```

### Запуск Discourse

После настройки скрипт автоматически запустит Discourse:

```bash
./launcher rebuild app
```

Это займет 5-10 минут.

### Проверка установки

1. Откройте браузер и перейдите на ваш домен:
   ```
   https://forum.fisherygroup.com
   ```

2. Завершите регистрацию администратора

3. Проверьте email для активации

## 🔐 Настройка SMTP

### SendGrid (рекомендуется)

1. Зарегистрируйтесь на [SendGrid](https://sendgrid.com/)
2. Создайте API ключ:
   - Settings → API Keys → Create API Key
   - Выберите "Full Access"
3. Используйте в настройках Discourse:
   - SMTP server: `smtp.sendgrid.net`
   - SMTP port: `587`
   - SMTP username: `apikey`
   - SMTP password: `ваш_api_ключ`

### Mailgun

1. Зарегистрируйтесь на [Mailgun](https://www.mailgun.com/)
2. Настройте домен
3. Используйте SMTP credentials:
   - SMTP server: `smtp.mailgun.org`
   - SMTP port: `587`
   - SMTP username: из Mailgun
   - SMTP password: из Mailgun

## 🔑 Создание API ключа для импорта

1. Войдите как администратор
2. Перейдите в **Admin** → **API**
3. Нажмите **New API Key**
4. Настройки:
   - **Description:** Migration Import
   - **User Level:** All Users
   - **Scope:** Global
5. Сохраните ключ в `config/discourse_config.yaml`

## 🔄 Обслуживание сервера

### Базовые команды Discourse

```bash
cd /var/discourse

# Перезапустить
./launcher restart app

# Остановить
./launcher stop app

# Запустить
./launcher start app

# Ребилд (после изменений конфигурации)
./launcher rebuild app

# Посмотреть логи
./launcher logs app

# Войти в контейнер
./launcher enter app
```

### Обновление Discourse

```bash
cd /var/discourse
git pull
./launcher rebuild app
```

### Резервное копирование

#### Ручное резервное копирование

```bash
cd /var/discourse
./launcher enter app
discourse backup
exit
```

Бэкапы сохраняются в `/var/discourse/shared/standalone/backups/default/`

#### Автоматическое резервное копирование

В админ-панели Discourse:
1. **Settings** → **Backups**
2. Включите `backup_frequency` (например, 1 день)
3. Настройте `backup_location` (S3, FTP и т.д.)

#### Digital Ocean Backups

Включите автоматические backups в настройках Droplet ($5-10/месяц):
1. Droplet → **Backups**
2. **Enable Backups**

## 📊 Мониторинг

### Установка htop для мониторинга ресурсов

```bash
apt install -y htop
htop
```

### Проверка использования диска

```bash
df -h
```

### Проверка памяти

```bash
free -h
```

### Мониторинг Docker контейнеров

```bash
docker ps
docker stats
```

## ⚠️ Решение проблем

### Discourse не запускается

```bash
cd /var/discourse
./launcher logs app
```

Проверьте логи на ошибки.

### Проблемы с email

1. Проверьте SMTP настройки в `/var/discourse/containers/app.yml`
2. Тестирование отправки email:
   ```bash
   ./launcher enter app
   rails c
   Email.send_test('your@email.com')
   ```

### Нехватка памяти

1. Проверьте использование памяти:
   ```bash
   free -h
   ```

2. Добавьте swap (см. выше) или увеличьте RAM Droplet

### Проблемы с SSL

Discourse автоматически настраивает Let's Encrypt. Если есть проблемы:

```bash
cd /var/discourse
./launcher rebuild app
```

## 🔗 Полезные ресурсы

- [Discourse Official Installation Guide](https://github.com/discourse/discourse/blob/main/docs/INSTALL-cloud.md)
- [Digital Ocean Discourse Tutorial](https://www.digitalocean.com/community/tutorials/how-to-install-discourse-on-ubuntu-20-04)
- [Discourse Meta](https://meta.discourse.org/) - официальный форум поддержки
- [Discourse Admin Guide](https://meta.discourse.org/t/discourse-admin-quick-start-guide/47370)

## 💰 Ориентировочные затраты

| Сервис | Стоимость |
|--------|-----------|
| Digital Ocean Droplet (4GB) | $24/месяц |
| Digital Ocean Backups | $5/месяц |
| Домен (.com) | $12/год |
| SendGrid (до 100 email/день) | Бесплатно |
| SendGrid (до 40,000 email/месяц) | $15/месяц |
| **Итого (минимум)** | ~**$30-45/месяц** |

---

**Примечание:** После настройки VPS вы будете готовы к импорту данных с помощью `scripts/run_importer.py`.

