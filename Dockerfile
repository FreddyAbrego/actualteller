FROM python:3.9-slim-buster
WORKDIR /app
COPY ./requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
RUN mkdir /app/data && chmod 755 /app/data
EXPOSE 5000
ENV FLASK_APP=app.py
CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]