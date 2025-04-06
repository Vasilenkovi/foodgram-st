# О проекте
Фудграмм - проект выполняемый в рамках курса по бекенд разработке на яндекс практикуме. Проект представляет собой платформу по работе с рецептами
# Технологии
- Django Rest Framework
- Djoser
- Gunicorn
- Postgres
- Nginx
# Шаги по развертке:
1.  Клонируйте репозиторий git clone https://github.com/Vasilenkovi/foodgram-st.git
2.  Создайте backend/foodgramm/foodgramm/.env и заполните согласнос примеру в backend/foodgramm/foodgramm/env-exapmple.txt данные для БД должные совпадать с данными в docker-compose
3.  Находясь в папке infra, выполните команду docker-compose up (это поднимет БД, выполнит миграции и загрузит список ингредиентов из папки data, и запустит приложение)
При необходимости можно вручную провести некоторые операции
1. Убрать из docker-compose.yml
```
python manage.py collectstatic --noinput && \
             python manage.py makemigrations && \
             python manage.py migrate && \
             python manage.py loader && \
```
2. Собрать статику
```  docker compose exec backend python manage.py collectstatic --noinput```
3. Создать миграции
```  docker compose exec backend python manage.py makemigrations```
4. Выполнить миграции
```  docker compose exec backend python manage.py migrate```
5. Импортировать ингредиенты
```  docker compose exec backend python manage.py loader```

Пример файла .env
```
DB_NAME=foodgram_db
USERNAME=foodgram_user
PASSWORD=423uoiasdfhSD23!
HOST=postgres
PORT=5432
SECRET_KEY='django-insecure-h&=kq&vcc41)0iy4^0h(&140bsj4ifr$y04p$5x0*!5$6ub3@g'
DEBUG=True
```
### Документация к API
Документация к API доступна по пути  
[http://127.0.0.1/api/docs/](http://127.0.0.1/api/docs/)

# Автор
Василенко Владимир Игоревич 
Контакт: vasvovaigor@gmail.com
