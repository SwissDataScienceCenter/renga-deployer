FROM python:3.6

# install the postgres driver
RUN apt-get -y update && apt-get -y install libpq-dev && apt-get clean

COPY . /code
WORKDIR /code

RUN pip install -e .[all]

# Set up our flask app
ENV FLASK_APP=sdsc_deployer.app:create_app

ENTRYPOINT ["./docker-entrypoint.sh"]

CMD ["flask", "run", "-h", "0.0.0.0"]

EXPOSE 5000
