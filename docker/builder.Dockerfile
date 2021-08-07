FROM node:12-alpine

RUN mkdir -p /home/node/app/node_modules && mkdir /home/node/app/build && chown -R node:node /home/node/app
VOLUME /home/node/app/build
WORKDIR /home/node/app
COPY --chown=node:node ./builder/package.json ./builder/yarn.lock ./
USER node
RUN yarn install --frozen-lockfile
COPY --chown=node:node ./builder ./

ENTRYPOINT ["yarn", "run"]
CMD ["watch"]
