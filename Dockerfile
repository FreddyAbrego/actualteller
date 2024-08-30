# Use the official Alpine Python image as a base image
FROM python:3-alpine

# Set the working directory in the container
WORKDIR /app

# Create a data directory and set permissions
RUN mkdir -p /app/data && chmod 777 /app/data

# Copy the current directory contents into the container at /app
COPY . .

# Install necessary system dependencies, including dbus
RUN apk update && apk add --no-cache \
    dbus \
    dbus-dev \
    # Add any other necessary dependencies here \
    && rm -rf /var/cache/apk/*
    
# Create a data directory and set permissions
RUN mkdir -p /app/data && chmod 755 /app/data

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000 to the outside world
EXPOSE 5000

# Run app.py when the container launches
CMD ["python3", "-u", "-m", "flask", "run", "--host=0.0.0.0"]