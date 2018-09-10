# Helm installation notes

https://docs.helm.sh/using_helm/

https://kubernetes.io/blog/2018/07/18/11-ways-not-to-get-hacked/
https://kubernetes.io/docs/tasks/administer-cluster/securing-a-cluster/

Installing and uninstalling helm:
```
helmins() {
    kubectl -n kube-system create serviceaccount tiller
    kubectl create clusterrolebinding tiller --clusterrole cluster-admin --serviceaccount=kube-system:tiller
    helm init --service-account=tiller
}

helmdel() {
    helm reset
    kubectl -n kube-system delete deployment tiller-deploy
    kubectl delete clusterrolebinding tiller
    kubectl -n kube-system delete serviceaccount tiller
}
```

Installing cert manager:
```
helm install --name cert-manager --namespace kube-system stable/cert-manager
```

