# Commands to run project

1. pip3/pip install -r requirements.txt
2. mkdir logs and sessions dir in project root dir
3. create .env file
4. python3 manage.py makemigrations - to create migrations file
5. python3 manage.py migrate - to apply migations to database
6. docker-compose up - to run redis 
7. python -m uvicorn telethondjangoproject.asgi:application --reload - to run project
8. python manage.py bot - to run app scheduler 