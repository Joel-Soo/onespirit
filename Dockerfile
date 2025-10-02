# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Install uv
RUN pip install uv

# Install git, curl, and vim
RUN apt-get update && apt-get install -y git curl vim && rm -rf /var/lib/apt/lists/*

# Copy the pyproject.toml and install dependencies
COPY pyproject.toml .
RUN uv pip install --system .

# Copy the rest of the application
COPY . .

# The command to run the application
# Replace this with the actual command to run your application
# CMD ["echo", "Please specify a command to run your application"]
