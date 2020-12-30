FROM node:12-alpine

RUN mkdir -p /home/node/app/node_modules && chown -R node:node /home/node/app
WORKDIR /home/node/app
COPY --chown=node:node ./builder/package.json ./builder/package-lock.json ./
USER node
RUN npm ci
COPY --chown=node:node ./builder ./

ENTRYPOINT ["npm", "run"]
CMD ["watch"]
