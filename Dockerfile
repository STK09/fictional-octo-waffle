# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Set environment variables (you can adjust or remove them if needed)
ENV BOT_TOKEN=7339125851:AAGSGhXjlDNtQPzYWlZpqp4WmuNMDTsiqIU
ENV OWNER_ID=5827289728
ENV MONGO_URI=mongodb+srv://jimiva5550:jimiva5550@cluster0.hy7t1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0

# Expose port (if you're using a web server, else you can skip this line)
EXPOSE 80

# Run the bot
CMD ["python", ".bot.py"]
