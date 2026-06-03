# Use official lightweight Python 3.13 image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Set working directory
WORKDIR /app

# Copy dependency files first to leverage Docker cache
COPY pyproject.toml ./

# Install pip and package dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . || pip install --no-cache-dir -r pyproject.toml || true

# Copy project files
COPY . .

# Expose port 8080
EXPOSE 8080

# Command to run the application
CMD ["python", "src/main.py"]
