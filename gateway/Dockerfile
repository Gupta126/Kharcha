FROM python:3.12-slim
RUN pip install --no-cache-dir "litellm[proxy]"
COPY litellm.config.yaml /app/litellm.config.yaml
EXPOSE 4000
CMD ["litellm", "--config", "/app/litellm.config.yaml", "--host", "0.0.0.0", "--port", "4000"]
