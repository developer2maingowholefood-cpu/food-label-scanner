FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies and Microsoft ODBC Driver 18
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    unixodbc-dev \
    freetds-dev \
    freetds-bin \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    curl \
    gnupg2 \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/instance /app/local_storage && \
    chmod 755 /app/instance /app/local_storage && \
    touch /app/instance/local.db && \
    chmod 666 /app/instance/local.db

# Create Azure startup script for database initialization
COPY startup-azure.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=src/app.py

# Expose port
EXPOSE 8000

# Run the startup script and then gunicorn
CMD ["/app/startup.sh"] 