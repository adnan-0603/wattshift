FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 WATTSHIFT_DATA=/data
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/* && useradd -u 10001 -m app
COPY requirements.lock.txt ./requirements.lock.txt
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY wattshift ./wattshift
COPY config ./config
COPY data/historical/prices.csv data/historical/provenance.json ./data/historical/
COPY data/summer/prices.csv data/summer/provenance.json ./data/summer/
COPY data/winter/prices.csv data/winter/provenance.json ./data/winter/
COPY apps/console/public/data/console.json ./seed/console.json
RUN mkdir -p /data && chown -R 10001:10001 /app /data
USER 10001
EXPOSE 8000
CMD ["python","-m","uvicorn","wattshift.api:app","--host","0.0.0.0","--port","8000"]
