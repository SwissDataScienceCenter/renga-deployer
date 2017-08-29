FROM python:3.6-alpine

# Install the PostgreSQL driver
RUN apk --no-cache add --update \
    postgresql-client \
    postgresql-dev \
    build-base \
    linux-headers

# Install only Python requirements
COPY setup.py README.rst CHANGES.rst /code/
COPY renga_deployer/version.py /code/renga_deployer/
WORKDIR /code
RUN pip install --no-cache-dir requirements-builder && \
    requirements-builder -e all -l pypi setup.py | pip install --no-cache-dir -r /dev/stdin && \
    pip uninstall -y requirements-builder

# Copy and install package
COPY . /code
RUN pip install --no-cache-dir -e .[all]

# Set up our flask app
ENV FLASK_APP=renga_deployer.wsgi:application

ENTRYPOINT ["./docker-entrypoint.sh"]

CMD ["flask", "run", "-h", "0.0.0.0"]

EXPOSE 5000
