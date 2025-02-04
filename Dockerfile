# Use official Python image from DockerHub
FROM python:3.9-slim

# Set environment variables to prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files (including bot.py) into the container
COPY . /app/

# Expose the port if needed (not mandatory for Telegram bots)
EXPOSE 8443

# Run the bot
CMD ["python", "bot.py"]
