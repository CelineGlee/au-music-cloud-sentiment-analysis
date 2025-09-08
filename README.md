# Cloud-based Social Media Sentiment Analysis on Australian Artists

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Prerequisites](#prerequisites)
4. [Deployment Instructions](#deployment-instructions)
5. [Installation Instructions](#installation-instructions)
6. [API Usage](#api-usage)
7. [Monitoring and Logging](#monitoring-and-logging)

## Overview
This cloud-native application ingests social media data from Mastodon and Reddit (BlueSky PoC), performs sentiment analysis on posts referencing global and Australian artists, and visualizes the results through Kibana and a Jupyter notebook front-end. The platform is deployed on the Melbourne Research Cloud using Kubernetes, Fission (serverless), Elasticsearch, Redis, FastAPI, Preometheus and Grafana.

## System Architecture
* **Backend:** Fission serverless functions (Python), Redis queue
* **Data Store:** Redis service with redis insight, Elasticsearch cluster with Kibana
* **Frontend/API:** Jupyter Notebook / FastAPI with OpenAPI documentation
* **ML Model:** HuggingFace transformer for sentiment analysis
* **Platform:** NeCTAR Research Cloud (OpenStack), Kubernetes with KEDA autoscaling
* **Monitor:** Prometheus, Grafana, Blackbox to monitor the system

## Prerequisites
Make sure you have the following installed locally or in your environment:
* `kubectl` (v1.22+)
* `helm` (v3+)
* `docker`
* Access to MRC dashboard and project
* A running Kubernetes cluster on NeCTAR (set up using `kubeadm`, `kubespray`, or similar)
* `fission` CLI (`brew install fission-cli` or from GitHub releases)
* `git`, `make`, `python3`, and `pip`
* Internet access for downloading container images and ML models
* Clone this repository:

```bash
git clone https://github.com/CelineGlee/au-music-cloud-sentiment-analysis.git
cd au-music-cloud-sentiment-analysis
```
## Deployment Instructions

**1. Deploy REDIS**
* Add the ot-helm repo and install the Redis Operator and Redis instance in the redis namespace using Helm.
* Create a Kubernetes secret redis-secret to store the Redis password.
* Monitor Redis pod status and verify functionality using Redis CLI commands (SET, GET).
* Deploy RedisInsight for GUI-based Redis management via a YAML file.
* Port-forward the RedisInsight service and connect using: redis://redis.redis.svc.cluster.local:6379

```bash
export REDIS_VERSION='0.19.1'
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm upgrade redis-operator ot-helm/redis-operator --install --namespace redis --create-namespace --version ${REDIS_VERSION}
kubectl create secret generic redis-secret --from-literal=password=password -n redis
helm upgrade redis ot-helm/redis \
  --install \
  --namespace redis \
  --version 0.16.5 \
  -f redis-values.yaml
kubectl get pods -n redis --watch
kubectl get pods -n redis -l app.kubernetes.io/name=redis
kubectl exec -n redis -it redis-0 -- bash
redis-cli -h 127.0.0.1
set test-key hello
get test-key
kubectl apply -f ./fission/redisinsight.yaml --namespace redis
kubectl port-forward service/redis-insight --namespace redis 5540:5540
browse http://localhost:5540/
add redis to redis insight GUI for management. redis://redis.redis.svc.cluster.local:6379
```

**2. Deploy Elastic Search**
* Set the desired Elasticsearch version and add the official Elastic Helm repository.
* Update the Helm repo to ensure the latest chart versions are available.
* Use helm upgrade --install to deploy Elasticsearch into the elastic namespace.
* Configure the deployment with 2 replicas, a predefined password, and a persistent volume using a specified storage class.
* Ensure sufficient storage is allocated (100Gi) for each Elasticsearch pod.

```bash
export ES_VERSION="8.5.1"
helm repo add elastic https://helm.elastic.co
helm repo update
helm upgrade --install \
  --version=${ES_VERSION} \
  --create-namespace \
  --namespace elastic \
  --set replicas=2 \
  --set secret.password="elastic"\
  --set volumeClaimTemplate.resources.requests.storage="100Gi" \
  --set volumeClaimTemplate.storageClassName="perfretain" \
  elasticsearch elastic/elasticsearch

```

**3. Deploy ML Jobs:**

> Please direct to backend/sentiment-score-model firstly

```bash
# Create a PersistentVolumeClaim (PVC) to store the ml model
kubectl apply -f persistent_store_model.yaml

# Build the Docker image
docker build -t your-docker-registry-name/sentiment-analyzer:lightweight -f Dockerfile .
docker push your-docker-registry-name/sentiment-analyzer:lightweight

# Deploy and Download the model into pvc
kubectl apply -f model-scripts-configmap.yaml
kubectl apply -f model-download-job.yaml

# Apply ConfigMaps for analyzing needed indices
kubectl apply -f reddit-comment-analyzer-script.yaml
kubectl apply -f reddit-comment-analyzer-configmap.yaml

kubectl apply -f reddit-sentiment-analyzer-script.yaml
kubectl apply -f reddit-sentiment-analyzer-configmap.yaml

kubectl apply -f mastodon-sentiment-analyzer-script.yaml
kubectl apply -f mastodon-sentiment-analyzer-configmap.yaml

kubectl apply -f sentiment-analyzer-index-configmap.yaml

# Apply the RBAC configuration
kubectl apply -f sentiment-rbac.yaml

# Apply the CronJobs
kubectl apply -f reddit-comment-analyzer-cronjob.yaml

kubectl apply -f reddit-sentiment-analyzer-cronjob.yaml

kubectl apply -f mastodon-sentiment-analyzer-cronjob.yaml

kubectl apply -f sentiment-analyzer-index-cronjob.yaml

# Track the process of each job (here using "reddit-comments-prod" as an example)
kubectl logs job/reddit-comment-shard0-job -n elastic
kubectl logs job/reddit-comment-shard1-job -n elastic
kubectl logs job/reddit-comment-shard2-job -n elastic
kubectl logs job/reddit-comment-shard3-job -n elastic
kubectl logs job/reddit-comment-shard4-job -n elastic
```

**4. Deploy FastAPI Backend:**
* After cloning the project, navigate to the analyser_api directory.
* Ensure your Docker Hub connection is properly configured.
* Build the Docker image and push it to Docker Hub.
* Use Helm to deploy the YAML configuration to the default namespace on the OpenStack Kubernetes cluster.
* Port forward to localhost:9090 and you may browse http://localhost:9090/docs to see the API docs.

```bash
cd au-music-cloud-sentiment-analysis/backend/analyser_api
docker build --platform=linux/amd64 -t <your dockerhub repo>/analyser_api:latest --push .
helm upgrade analyser-api ./analyser_api --install --namespace default
kubectl -n default port-forward svc/analyser-api 9090:9090
Browse http://localhost:9090/docs
```

**5. Deploy KEDA (Kubernetes Event-Driven Autoscaling):**
* Deploy KEDA using the Helm chart in the keda namespace, specifying version 2.9.
* Apply the ScaledObject YAML to monitor the Redis queue for autoscaling.

```bash
export KEDA_VERSION='2.9'
helm repo add kedacore https://kedacore.github.io/charts
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm repo update
helm upgrade keda kedacore/keda --install --namespace keda --create-namespace --version ${KEDA_VERSION}
kubectl apply -f scaled-object.yaml
```

**6. Access Kibana (optional):** Forward port from your cluster:

```bash
kubectl port-forward service/elasticsearch-kibana 5601:5601 # Then open http://localhost:5601 in browser
```

**7. Prometheus, Blackbox, Grafana Dashboard: Monitoring and Real-time visualisation:**
* Installing the full Prometheus/Grafana monitoring stack.
* Adding the Blackbox Exporter to probe endpoints.
* Configuring probes (via ConfigMap).
* Instructing Prometheus to scrape Blackbox Exporter.
* Monitoring your Elasticsearch endpoint using Blackbox.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack -n monitor -f values-monitor.yaml

helm install prometheus-blackbox-exporter prometheus-community/prometheus-blackbox-exporter \
  --namespace monitor \
  --set serviceMonitor.enabled=true

kubectl apply -f blackbox-exporter-cm.yaml

helm upgrade prometheus-blackbox-exporter prometheus-community/prometheus-blackbox-exporter \
  --namespace monitor \
  -f blackbox-exporter-values.yaml

kubectl apply -f elasticsearch-blackbox-servicemonitor.yaml

helm repo update
helm upgrade prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitor \
  --set prometheusOperator.enabled=true
```

## Installation Instructions

Install and configure Fission on your Kubernetes cluster:

```bash
fission install --spec --builder
```

Prepare Fission Functions:

```bash
cd fission
fission spec init
fission spec apply
```

Start Preprocessors & Harvesters:

```bash
kubectl apply -f kubernetes/harvesters.yaml
kubectl apply -f kubernetes/preprocessors.yaml
```


## API Usage
The FastAPI server exposes the following endpoints:
* `/total-artists-mention-count`: Returns the total number of posts mentioning artists, both internationally and in Australia.
* `/mention-count-by-artist-final`: Returns the number of posts mentioning each artist worldwide.
* `/sentiment_trends_per_artist`: Returns the sentiment trend over time for a given artist.
* `/sentiment-distribution-by-artist`: Returns the overall sentiment distribution for a specific artist.
* `/last-post-time`: Returns the timestamp of the most recent social media post within our summary index.
* `/health`: Returns the current status of the Analyser API service.

Port forward then open browser to access the interactive documentation at http://localhost:9090/docs

```bash
kubectl -n default port-forward svc/analyser-api 9090:9090
```

## Monitoring and Logging
* **Grafana:**
The Grafana Dashboard is located at http://localhost:3000/ after port-forward.

```bash
kubectl -n monitor port-forward svc/prometheus-grafana 3000:80
```

* **Function Status:**
```bash
fission fn logs --name reddit-harvester
```

* **Pod Status:**

```bash
kubectl get pods -A
kubectl logs <pod-name>
```
