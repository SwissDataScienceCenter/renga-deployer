FROM python:alpine

# install the postgres driver
RUN apk update && apk add postgresql-client postgresql-dev build-base python-dev linux-headers

COPY . /code
WORKDIR /code

RUN pip install -e .[all]

# Set up our flask app
ENV FLASK_APP=renga_deployer.wsgi:application

ENTRYPOINT ["./docker-entrypoint.sh"]

CMD ["flask", "run", "-h", "0.0.0.0"]

EXPOSE 5000
