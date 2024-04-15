# Use a minimal Python base image
FROM python:3.9

# Create a working directory within the container
WORKDIR /app

# Copy requirements.txt (if you have one)
COPY requirements.txt .
# Install dependencies (if using requirements.txt)
RUN pip install -r requirements.txt

# Copy your Python application files
COPY . .

# Expose the port where your Flask app runs (usually 5000)
EXPOSE 5000

# Run the Python script to start your Flask application
CMD ["python", "app.py"]
