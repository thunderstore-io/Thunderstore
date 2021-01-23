FROM node:14-alpine

RUN mkdir -p /home/node/app/node_modules && mkdir /home/node/app/build && chown -R node:node /home/node/app
VOLUME /home/node/app/build
WORKDIR /home/node/app
COPY --chown=node:node ./builder/package.json ./builder/package-lock.json ./
USER node
RUN npm ci
COPY --chown=node:node ./builder ./

ENTRYPOINT ["npm", "run"]
CMD ["watch"]
