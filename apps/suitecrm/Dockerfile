# SuiteCRM lightweight image -- in real life we'd use the upstream `bitnami/suitecrm`
# image; for this PoC we only need the schema migrations + extractor to demonstrate
# the data-producing app pipeline path.
FROM python:3.11-slim

WORKDIR /opt/suitecrm

RUN apt-get update \
 && apt-get install -y --no-install-recommends default-mysql-client jq curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /opt/suitecrm/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY migrations /opt/suitecrm/migrations
COPY extractor /opt/suitecrm/extractor

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python"]
CMD ["-m", "extractor.serve"]
