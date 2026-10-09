FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN pip install --no-cache-dir uv && \
    uv pip install --system fastapi uvicorn[standard]

# Copy application code
COPY . .

# Expose port
EXPOSE 8090

# Set environment variables
ENV PYTHONPATH=/app

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
