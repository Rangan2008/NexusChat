# Use a specific Python version to ensure consistency
FROM python:3.10.12-slim-bullseye

# Set the working directory inside the container
WORKDIR /app

# Prevent apt-get from asking for user input
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists and install all system dependencies from your script
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libmupdf-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    build-essential \
    pkg-config \
    # Clean up apt cache to keep the image small
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy your requirements file and install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Expose the port that Gunicorn will run on
EXPOSE 10000

# Command to run your application using Gunicorn (from your Procfile)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
