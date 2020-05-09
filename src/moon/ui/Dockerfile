# Dockerfile for SST Mosaic Pipeline lunar UI
FROM node:13
WORKDIR /usr/src/nacpl_ui
COPY package*.json ./
RUN npm install
COPY . ./
EXPOSE 1234
CMD [ "npm", "start" ]