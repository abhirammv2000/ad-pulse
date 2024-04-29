# Use an official Node.js runtime as the base image
FROM node:14-alpine

# Set the working directory in the container
WORKDIR /app

# Copy the package.json and package-lock.json files to the container
COPY package*.json ./

# Install the dependencies
RUN npm install --force

# Copy the app source code to the container
COPY . .

# Build the app
RUN npm run build

# Expose the port on which the app will run
EXPOSE 3000

# Define the command to run the app
CMD ["npm", "start"]