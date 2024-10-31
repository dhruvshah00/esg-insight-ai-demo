# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install ca-certificates and ping utilities
RUN apt-get update && apt-get install -y curl ca-certificates iputils-ping

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies with SSL verification disabled
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy the rest of the application code
COPY . .

# Command to run the FastAPI backend
CMD ["python", "run.py"]
