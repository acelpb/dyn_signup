FROM registry.fedoraproject.org/fedora-minimal:latest

RUN microdnf install -y python3.13 uv df && microdnf clean all
ENV PYTHONUNBUFFERED=1

RUN mkdir /app
WORKDIR /app

COPY ./uv.lock uv.lock
COPY ./pyproject.toml pyproject.toml
RUN uv sync --frozen --no-install-project --compile-bytecode

COPY ./ .
RUN uv run python manage.py collectstatic --noinput

CMD uv run gunicorn dynasignup.wsgi:application --bind 0.0.0.0:9000
