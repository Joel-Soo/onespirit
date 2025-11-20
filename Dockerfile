# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install uv
RUN pip install uv

# Install git, curl, and vim
RUN apt-get update && apt-get install -y git curl vim && rm -rf /var/lib/apt/lists/*

# Copy dependency files (pyproject.toml and uv.lock)
COPY pyproject.toml uv.lock ./

# Set uv environment location
ENV UV_PROJECT_ENVIRONMENT=/usr/local

# Install dependencies using uv.lock for reproducible builds
RUN uv sync --frozen

# Copy the rest of the application
COPY . .

# Run the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
# CMD ["tail", "-f", "/dev/null"]`