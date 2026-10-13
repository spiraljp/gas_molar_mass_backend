# Gas Molar Mass Backend
Backend-приложение на FastAPI для каталога газов и расчета молярной массы.
В ЛР4 реализовано завершение backend для будущего SPA: REST API, авторизация через cookie-сессии, хранение сессий в Redis, работа с PostgreSQL и MinIO.
## Запуск проекта
1. Запустить контейнеры:
docker compose up -d
2. Активировать виртуальное окружение:
source gas-molar-mass-webapp/bin/activate
3. Запустить сервер:
uvicorn main:app --reload
Адрес API:
http://127.0.0.1:8000
Swagger:
http://127.0.0.1:8000/docs
Adminer:
http://127.0.0.1:8081
MinIO:
http://127.0.0.1:9001
Redis:
localhost:6379
## Используемые технологии
Python
FastAPI
PostgreSQL
SQLAlchemy ORM
Alembic
Redis
MinIO
Docker Compose
Postman
Swagger
## Статусы газа
draft — черновик
published — опубликован
deleted — логически удален
Записи со статусом deleted не передаются клиенту в списке и ленте.
## Авторизация
В ЛР4 реализована авторизация через cookie-сессии.
Пользователь выполняет POST /api/users/login.
Backend проверяет username и password.
Если данные верные, backend создает session_id.
session_id сохраняется в Redis.
Клиенту отправляется cookie session_id.
В следующих запросах backend получает session_id из cookie и определяет текущего пользователя через Redis.
Пример значения в Redis:
{
  "user_id": 6
}
Cookie:
session_id
Свойства cookie:
HttpOnly
SameSite=Lax
## Redis
Redis используется для хранения сессий пользователей.
Ключ сессии имеет вид:
session:<uuid>
Пример:
session:28fe5128-f042-4b66-b4f6-75542e1d0e5c
Проверка Redis:
docker exec -it gas_redis redis-cli keys '*'
docker exec -it gas_redis redis-cli get "session:<uuid>"
При logout сессия удаляется из Redis, а cookie очищается.
## MinIO
MinIO используется для хранения файлов изображений и видео.
Файлы загружаются при создании газа через POST /api/gases.
В таблице gases хранятся не сами файлы, а URL файлов.
Поля:
gas_image_url
gas_video_url
Пример URL:
http://localhost:9000/gas-media/file.png
## Доступы
Гость может выполнять методы чтения:
GET /api/gases
GET /api/gases/feed
Авторизованный пользователь может выполнять методы создателя:
GET /api/gases/draft
POST /api/gases
PUT /api/gases/{gas_id}/publish
DELETE /api/gases/{gas_id}
POST /api/gases/{gas_id}/like
POST /api/users/logout
Регистрация и login доступны без авторизации:
POST /api/users/register
POST /api/users/login
## API методы
### GET /api/gases
Получить список опубликованных газов.
Доступ:
гость
авторизованный пользователь
Query-параметр:
search — строка поиска по названию газа
Пример:
GET /api/gases?search=азот
Ответ содержит признаки:
is_owner — 1, если текущий пользователь является создателем газа, иначе 0
is_liked — 1, если текущий пользователь поставил лайк, иначе 0
likes_count — количество лайков
### GET /api/gases/feed
Получить газ для ленты.
Доступ:
гость
авторизованный пользователь
Без параметров возвращает первый опубликованный газ:
GET /api/gases/feed
С query-параметрами может вернуть газ по id или следующий опубликованный газ:
GET /api/gases/feed?gas_id=2&next=true
Query-параметры:
gas_id — id текущего газа
next — если true, возвращается следующий опубликованный газ
### GET /api/gases/draft
Получить черновик текущего пользователя.
Доступ:
только авторизованный пользователь
Id не передается, потому что у пользователя может быть не более одного черновика.
GET /api/gases/draft
Если пользователь не авторизован, возвращается 401.
### POST /api/gases
Создать новый газ в статусе draft и загрузить фото/видео в MinIO.
Доступ:
только авторизованный пользователь
Тип запроса:
multipart/form-data
Поля:
gas_name — название газа
image — файл изображения
video — файл короткого видео
Системные поля id, gas_status, creator_id, created_at вычисляются на backend.
creator_id берется из текущей cookie-сессии.
### PUT /api/gases/{gas_id}/publish
Опубликовать черновик текущего пользователя.
Доступ:
только авторизованный пользователь
Body:
{
  "molar_mass": 20.18,
  "density_normal_conditions": 0.9002
}
Backend меняет статус на published и заполняет formed_at.
Если пользователь не авторизован, возвращается 401.
Если газ не найден или не принадлежит пользователю, публикация не выполняется.
### DELETE /api/gases/{gas_id}
Логически удалить газ текущего пользователя.
Доступ:
только авторизованный пользователь
DELETE /api/gases/7
Физического удаления из БД нет.
Статус меняется на deleted.
### POST /api/gases/{gas_id}/like
Поставить или убрать лайк от текущего пользователя.
Доступ:
только авторизованный пользователь
Body:
{
  "value": 1
}
value = 1 — поставить лайк
value = 0 — убрать лайк
Лайк сохраняется в таблице gas_likes.
### POST /api/users/register
Зарегистрировать пользователя.
Доступ:
гость
Body:
{
  "username": "lab4_user",
  "password": "12345"
}
Пароль сохраняется не в открытом виде, а как password_hash.
### POST /api/users/login
Аутентифицировать пользователя.
Доступ:
гость
Body:
{
  "username": "lab4_user",
  "password": "12345"
}
При успешной аутентификации backend:
создает session_id;
сохраняет user_id в Redis;
отправляет cookie session_id клиенту.
### POST /api/users/logout
Выполнить выход из системы.
Доступ:
авторизованный пользователь
Backend:
получает session_id из cookie;
удаляет сессию из Redis;
очищает cookie session_id.
## Таблицы БД
### app_users
Пользователи приложения.
Поля:
id — integer, первичный ключ
username — varchar, имя пользователя
password_hash — varchar, хэш пароля
### gases
Карточки газов.
Поля:
id — integer, первичный ключ
gas_name — varchar, название газа
gas_formula — varchar, формула газа
short_description — varchar, краткое описание
gas_status — varchar, статус газа: draft, published, deleted
gas_image_url — varchar, URL изображения в MinIO
gas_video_url — varchar, URL видео в MinIO
molar_mass — float, молярная масса
density_normal_conditions — float, плотность при н.у.
created_at — datetime, дата создания
formed_at — datetime, дата публикации
creator_id — integer, внешний ключ на app_users.id
### gas_likes
Таблица лайков.
Поля:
id — integer, первичный ключ
user_id — integer, внешний ключ на app_users.id
gas_id — integer, внешний ключ на gases.id
Таблица gas_likes связывает пользователей и газы.
Один пользователь может поставить лайки многим газам.
Один газ может иметь лайки от многих пользователей.
## Бизнес-логика
- Клиент не передает системные поля: id, gas_status, creator_id, created_at, formed_at.
- Системные поля вычисляются на backend.
- У текущего пользователя может быть не более одного газа в статусе draft.
- Опубликовать можно только свой черновик.
- Удалить можно только свой газ.
- Удаление выполняется как soft delete: статус меняется на deleted.
- Вернуть published или deleted обратно в draft нельзя.
- Записи со статусом deleted не передаются клиенту.
- Создание, публикация, удаление, получение черновика и лайки требуют авторизации.
- GET-методы списка и ленты доступны гостю.
## Swagger
Swagger доступен по адресу:
http://127.0.0.1:8000/docs
В Swagger описаны методы API.
Для проверки авторизации нужно выполнить POST /api/users/login.
После успешного login браузер получает cookie session_id.
После этого защищенные методы можно выполнять через Swagger в том же окне браузера.
