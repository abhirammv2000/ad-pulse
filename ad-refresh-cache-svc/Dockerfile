# Use a base image
FROM python:3.8.2

# Copy the Python file to the container
COPY refresh-cache.py /refresh-cache.py

# Install requirements
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

# Set the working directory
WORKDIR /

# Run the Python file
CMD ["python", "refresh-cache.py"]