FROM node:12.2.0-alpine

WORKDIR /app
COPY ./builder/package.json ./builder/package-lock.json /app/
RUN npm ci
COPY ./builder /app

ENTRYPOINT ["npm", "run"]
CMD ["watch"]
