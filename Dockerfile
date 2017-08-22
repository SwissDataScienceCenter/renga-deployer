FROM python:3.6

# install the postgres driver
RUN apt-get -y update && apt-get -y install libpq-dev && apt-get clean

COPY . /code
WORKDIR /code

RUN pip install -e .[all]

# Set up our flask app
ENV FLASK_APP=/code/sdsc_deployer/app.py

ENTRYPOINT ["./run_app.sh"]

EXPOSE 5000
