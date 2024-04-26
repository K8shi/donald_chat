FROM python:3.11

# ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

ADD . .

RUN pip install -r requirements.txt

# CMD ["python", "manage.py", "runserver"]
EXPOSE 8000