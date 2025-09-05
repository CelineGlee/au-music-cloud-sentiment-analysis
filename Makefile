# Port-forward multiple services
run-port-forwards:
	kubectl -n elastic port-forward svc/kibana-kibana 5601:5601 &
	kubectl -n redis port-forward svc/redis-insight 5540:5540 &
	kubectl -n monitor port-forward svc/prometheus-grafana 3000:80 &
	kubectl -n elastic port-forward svc/elasticsearch-master 9200:9200 &
	kubectl -n fission port-forward svc/router 8888:80 &
	kubectl -n default port-forward svc/analyser-api 9090:9090 &

# Stop all port-forwards (brute force)
kill-port-forwards:
	pkill -f "port-forward"