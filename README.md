# Gas Molar Mass Backend

Backend-приложение на FastAPI для каталога газов и расчета молярной массы.
В ЛР3 реализован REST API для будущего SPA.

## Запуск проекта

1. Запустить контейнеры:

docker compose up -d

2. Активировать виртуальное окружение:

source gas-molar-mass-webapp/bin/activate

3. Запустить сервер:

uvicorn main:app --reload

Адрес API:

http://127.0.0.1:8000

Adminer:

http://127.0.0.1:8081

MinIO:

http://127.0.0.1:9001

## Статусы газа

draft — черновик
published — опубликован
deleted — логически удален

Удаленные записи не передаются клиенту.

## Текущий пользователь

В ЛР3 авторизация еще не реализуется.
Текущий пользователь задан константой через функцию get_current_user_id().

CURRENT_USER_ID = 1

def get_current_user_id() -> int:
    return CURRENT_USER_ID

## API методы

### GET /api/gases

Получить список опубликованных газов с фильтрацией.

Query-параметр:

search — строка поиска по названию газа

Пример:

GET /api/gases?search=азот

Ответ содержит признак:

is_owner — 1, если текущий пользователь является создателем газа, иначе 0

### GET /api/gases/feed

Получить первый опубликованный газ для ленты.

GET /api/gases/feed

### GET /api/gases/draft

Получить черновик текущего пользователя.
Id не передается, потому что у пользователя может быть не более одного черновика.

GET /api/gases/draft

### POST /api/gases

Создать новый газ в статусе draft и загрузить фото/видео в MinIO.

Тип запроса:

multipart/form-data

Поля:

gas_name — название газа
image — файл изображения
video — файл короткого видео

Системные поля id, gas_status, creator_id, created_at вычисляются на backend.

### PUT /api/gases/{gas_id}/publish

Опубликовать черновик текущего пользователя.

Body:

{
  "molar_mass": 20.18,
  "density_normal_conditions": 0.9002
}

Backend меняет статус на published и заполняет formed_at.

### DELETE /api/gases/{gas_id}

Логически удалить газ текущего пользователя.

DELETE /api/gases/7

Физического удаления из БД нет. Статус меняется на deleted.

### POST /api/gases/{gas_id}/like

Поставить или убрать лайк от текущего пользователя.

Body:

{
  "value": 1
}

value = 1 — поставить лайк
value = 0 — убрать лайк

### POST /api/users/register

Зарегистрировать пользователя.

Body:

{
  "username": "lab3_user",
  "password": "12345"
}

Пароль сохраняется как password_hash.

### POST /api/users/login

Заглушка аутентификации для ЛР4.

Body:

{
  "username": "lab3_user",
  "password": "12345"
}

### POST /api/users/logout

Заглушка деавторизации для ЛР4.

POST /api/users/logout

## Таблицы БД

### app_users

Пользователи приложения.

Поля:

id — integer, первичный ключ
username — varchar(50), имя пользователя, уникальное
password_hash — varchar(255), хэш пароля

### gases

Карточки газов.

Поля:

id — integer, первичный ключ
gas_name — varchar(100), название газа
gas_formula — varchar(20), формула газа
short_description — varchar(500), краткое описание
gas_status — varchar(20), статус: draft, published, deleted
gas_image_url — varchar(255), URL изображения в MinIO
gas_video_url — varchar(255), URL видео в MinIO
molar_mass — float, молярная масса
density_normal_conditions — float, плотность при н.у.
created_at — datetime, дата создания
formed_at — datetime, дата публикации
creator_id — integer, внешний ключ на app_users.id

### gas_likes

Связь многие-ко-многим между пользователями и газами.

Поля:

id — integer, первичный ключ
user_id — integer, внешний ключ на app_users.id
gas_id — integer, внешний ключ на gases.id

## MinIO

Файлы изображений и видео хранятся в MinIO в бакете gas-media.

В таблице gases сохраняются только URL файлов:

gas_image_url
gas_video_url

Пример URL:

http://localhost:9000/gas-media/file.png

## Особенности бизнес-логики

- Клиент не передает системные поля: id, gas_status, creator_id, created_at, formed_at.
- Системные поля вычисляются на backend.
- У текущего пользователя может быть не более одного газа в статусе draft.
- Записи со статусом deleted не передаются клиенту.
- Удаление газа выполняется как soft delete: статус меняется на deleted.
- Вернуть опубликованный или удаленный газ обратно в draft нельзя.
- Авторизация в ЛР3 не реализуется, текущий пользователь задан через singleton-функцию.
