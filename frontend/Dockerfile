FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
COPY . .

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
