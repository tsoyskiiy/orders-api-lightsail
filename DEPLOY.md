# DEPLOY.md — Orders API на AWS Lightsail

Стек: FastAPI + PostgreSQL (`pgvector/pgvector:pg16`) в Docker Compose на одной VM Ubuntu.

## Результаты (заполнить после развёртывания)

| Что | Значение |
|---|---|
| Публичный URL `/docs` | `http://<ВАШ-IP>:8000/docs` |
| Скриншот Swagger UI с сервера | `screenshots/swagger.png` |
| `docker compose ps` на сервере | см. раздел 5 |
| Повторное развёртывание | см. раздел 6 |

---

## 1. Локальный запуск и проверка

```bash
cp .env.example .env            # впишите свои значения
docker build -t orders-api:1.0 .
docker compose up -d --build
docker compose ps               # db → (healthy), api → Up
```

Откройте http://localhost:8000/docs. Таблицы `users`, `products`, `orders`, `documents` создаются автоматически при старте API.

Проверка аутентификации в `/docs`:
1. `POST /auth/register` — создайте пользователя.
2. Кнопка **Authorize** → email в поле `username`, пароль → Authorize.
3. `GET /users/me` вернёт вашего пользователя (без токена — `401`).

## 2. Подготовка сервера

В консоли Lightsail: **Create instance** → Linux/Unix → **OS Only → Ubuntu 22.04/24.04** → план от 1 GB RAM → скачайте key pair (`.pem`).

```bash
chmod 600 ~/Downloads/LightsailDefaultKey.pem
ssh -i ~/Downloads/LightsailDefaultKey.pem ubuntu@<ВАШ-IP>
```

На сервере:

```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh     # Docker + плагин compose
sudo usermod -aG docker $USER
exit                                            # перелогиньтесь, чтобы группа применилась
```

```bash
ssh -i ~/Downloads/LightsailDefaultKey.pem ubuntu@<ВАШ-IP>
docker run --rm hello-world                     # без sudo
docker compose version
```

## 3. Развёртывание

```bash
git clone <URL-вашего-репозитория> orders-api && cd orders-api
cp .env.example .env
# Продакшен-секреты — только на сервере, не из репозитория:
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" .env
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" .env
chmod 600 .env

docker compose up -d --build
docker compose ps
```

## 4. Файрвол

Lightsail → инстанс → **Networking** → IPv4 Firewall → **Add rule**: Custom, TCP, порт **8000**.
Порт 5432 **не открываем** — БД доступна только внутри сети compose.

Откройте в браузере `http://<ВАШ-IP>:8000/docs`.

## 5. Вывод `docker compose ps`

```text
<вставьте вывод с сервера: db — Up (healthy), api — Up>
```

## 6. Повторное развёртывание (обновление)

Изменение: новый эндпоинт только для чтения `GET /stats` (количество записей в таблицах). Добавьте в конец `app/main.py`:

```python
@app.get("/stats", tags=["service"])
def stats(db: Session = Depends(get_db)):
    count = lambda m: db.scalar(select(func.count()).select_from(m))
    return {
        "users": count(models.User),
        "products": count(models.Product),
        "orders": count(models.Order),
        "documents": count(models.Document),
    }
```

и в импорте замените `from sqlalchemy import select, text` на `from sqlalchemy import func, select, text`. Также поднимите `version="1.0"` → `"1.1"`.

Перед обновлением создайте тестовые данные (пользователь, товар, заказ) и запомните `GET /stats` / `GET /orders`.

```bash
# локально
git add -A && git commit -m "Add GET /stats" && git push

# на сервере
cd orders-api && ./deploy.sh        # git pull && docker compose up -d --build && docker compose ps
```

Проверка: `curl http://<ВАШ-IP>:8000/stats` работает, `/health` показывает `1.1`, а ранее созданные данные на месте — они лежат в именованном томе `pgdata`, который `up --build` не трогает.

> ⚠️ Не используйте `docker compose down -v` — флаг `-v` удаляет том с данными.

Заметка об изменении и подтверждение сохранности данных: `<заполнить>`

## 7. Бонус: резервная копия

```bash
mkdir -p backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backups/orders_$(date +%F).sql
```

Расписание (cron, `crontab -e`):

```cron
0 3 * * * cd /home/ubuntu/orders-api && docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backups/orders_$(date +\%F).sql
```
