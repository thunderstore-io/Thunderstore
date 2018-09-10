# Kubernetes deployment configuration

## Resources

https://medium.com/google-cloud/kubernetes-nodeport-vs-loadbalancer-vs-ingress-when-should-i-use-what-922f010849e0
https://medium.com/@markgituma/kubernetes-local-to-production-with-django-3-postgres-with-migrations-on-minikube-31f2baa8926e

## Manual initial steps

Create the project namespace
```
kubectl create -f namespace.yaml
```

Create the deployment user role
```
kubectl create -f role.yaml
```

At this point you should create a service account via the Google Cloud console with access to the Kubernetes cluster.

Bind a service account to the role
```
kubectl create rolebinding deployment-role-binding --role=deployment --user=serviceaccount@email.com --namespace nexus
```

Create secrets
```
kubectl create secret generic nexus --from-literal=DISCORD_TOKEN='...' --from-literal=GITHUB_TOKEN='...' --namespace nexus
```

## Automatic steps (Ran by Travis CI)

Building the container image and pushing to Dockerhub
```
docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD;
docker build --tag $IMAGE:commit-$TRAVIS_COMMIT .
docker push $IMAGE:commit-$TRAVIS_COMMIT
```

Deploying the container
```
if [ ! -d "$HOME/google-cloud-sdk/bin" ]; then rm -rf $HOME/google-cloud-sdk; export CLOUDSDK_CORE_DISABLE_PROMPTS=1; curl https://sdk.cloud.google.com | bash; fi
source $HOME/google-cloud-sdk/path.bash.inc
gcloud components install kubectl
cd kubernetes
openssl aes-256-cbc -k "$SERVICE_ACCOUNT_PASSWORD" -in service-account.json.enc -out service-account.json -d
gcloud auth activate-service-account <service-account@project.iam.gserviceaccount.com> --key-file=service-account.json --project=<project>
gcloud config set core/project <project>
gcloud config set compute/zone europe-north1-a
gcloud container clusters get-credentials <cluster>
envsubst '${TRAVIS_COMMIT}' < deployment.yaml.template > deployment.yaml
kubectl apply -f deployment.yaml
```

## Good to know Google Cloud and kubectl commands

Disables kubernetes web UI from the cluster
```
gcloud container clusters update "${CLUSTER_NAME}" --update-addons=KubernetesDashboard=DISABLED
```

Disables kubernetes legacy authorization from the cluster
```
gcloud container clusters update "${CLUSTER_NAME}" --no-enable-legacy-authorization
```

Authorizes your Google Cloud account with the cluster-admin role in that cluster. **User email is case sensitive**
```
kubectl create clusterrolebinding cluster-admin-binding --clusterrole=cluster-admin --user=SomeAccount@gmail.com
```

Create a global static IP:

```
gcloud compute addresses create nexus --global
gcloud compute address describe nexus --global
```

Setting up a cloud SQL instance: https://cloud.google.com/sql/docs/mysql/connect-kubernetes-engine

Running migrations for Django:

```
kubectl exec --namespace nexus nexus-deployment-787664c9dc-tngzr -- python manage.py migrate
```

## Encrypting the google service account authentication file

https://docs.travis-ci.com/user/encrypting-files/

Launching a ruby container on Windows git bash with the current directory mounted
```
winpty docker run --rm -it -v ${PWD:0:2}:${PWD:2}://data ruby:2.3.7-jessie //bin/bash
```

Linux
```
docker run --rm -it -v $(pwd):/data ruby:2.3.7-jessie /bin/bash
```

Installing Travis
```
gem install travis
```

At this point you should generate a password to be used for encryption/decryption. Example will use 1234

Encrypting the password
```
travis encrypt SERVICE_ACCOUNT_PASSWORD=1234
```

Encrypting the service account json file with OpenSSL
```
openssl aes-256-cbc -k "1234" -in service-account.json -out service-account.json.enc
```

