# Use an official Python runtime as a parent image
FROM python:3

# Install necessary system dependencies, including dbus
RUN apt-get update && apt-get install -y \
    dbus \
    libdbus-1-dev \
    # Add any other necessary dependencies here \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .

# Create a data directory and set permissions
RUN mkdir /app/data && chmod 777 /app/data

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8002 available to the world outside this container
EXPOSE 8002

# Run app.py when the container launches
CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]
