FROM node:12.2.0-alpine

WORKDIR /app

ENTRYPOINT ["npm", "run"]
CMD ["watch"]
