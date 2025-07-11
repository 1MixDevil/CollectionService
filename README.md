# CollectionService

## CollectType API

| Метод   | Путь                 | Описание                       | Тело запроса           | Ответ (модель)       |
|---------|----------------------|--------------------------------|------------------------|----------------------|
| GET     | `/figure/types/`     | Список всех типов коллекции    | —                      | `List[CollectTypeRead]` |
| POST    | `/figure/types/`     | Создать новый тип              | `CollectTypeCreate`    | `CollectTypeRead`    |
| GET     | `/figure/types/{id}` | Получить один тип по ID        | —                      | `CollectTypeRead`    |
| PATCH   | `/figure/types/{id}` | Обновить название типа         | `CollectTypeCreate`    | `CollectTypeRead`    |
| DELETE  | `/figure/types/{id}` | Удалить тип                    | —                      | _204 No Content_     |

---

## Figure API

| Метод   | Путь                 | Описание                       | Тело запроса           | Ответ (модель)        |
|---------|----------------------|--------------------------------|------------------------|-----------------------|
| GET     | `/figure/`           | Список всех фигур              | —                      | `List[FigureRead]`    |
| POST    | `/figure/`           | Создать новую фигурку          | `FigureCreate`         | `FigureRead`          |
| GET     | `/figure/{id}`       | Подробности фигурки (с владельцами и ценами) | —       | `FigureDetail`        |
| PATCH   | `/figure/{id}`       | Обновить данные фигурки        | `FigureUpdate`         | `FigureRead`          |
| DELETE  | `/figure/{id}`       | Удалить фигурку                | —                      | _204 No Content_      |

---

## User–Figure (FigureToUser) API

| Метод   | Путь                          | Описание                                            | Тело запроса            | Ответ (модель)          |
|---------|-------------------------------|-----------------------------------------------------|-------------------------|-------------------------|
| GET     | `/figure/user/{user_id}/`     | Список всех записей владения фигурками для пользователя | —                   | `List[FigureToUserRead]` |
| POST    | `/figure/user/`               | Добавить фигурку пользователю                       | `FigureToUserCreate`    | `FigureToUserRead`      |
| PATCH   | `/figure/user/{rec_id}`       | Обновить запись владения фигуркой                   | `FigureToUserUpdate`    | `FigureToUserRead`      |
| DELETE  | `/figure/user/{rec_id}`       | Удалить запись владения фигуркой                    | —                       | _204 No Content_        |
