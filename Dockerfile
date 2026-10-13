# Ranq container. Build with JS rendering support:
#   docker build --build-arg WITH_BROWSER=1 -t ranq .
# Run (reports land in ./ranq-report on the host):
#   docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" ranq audit https://example.com
FROM python:3.11-slim

ARG WITH_BROWSER=0
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --upgrade pip \
    && if [ "$WITH_BROWSER" = "1" ]; then \
         pip install ".[full]" && playwright install --with-deps chromium; \
       else pip install ".[keywords,google]"; fi

RUN useradd --create-home --uid 10001 ranq && mkdir /work && chown ranq /work
USER ranq
WORKDIR /work
ENTRYPOINT ["ranq"]
CMD ["--help"]
