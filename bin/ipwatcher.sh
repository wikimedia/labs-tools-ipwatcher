#!/usr/bin/env bash

source /data/project/ipwatcher/www/python/venv/bin/activate

_get_pod() {
    kubectl get pods \
        --output=jsonpath={.items..metadata.name} \
        --selector=name=ipwatcher.bot
}

case "$1" in
    start)
        echo "Starting ipwatcher"
        kubectl create -f /data/project/ipwatcher/etc/deployment.yaml
        ;;
    run)
        date +%Y-%m-%dT%H:%M:%S
        echo "Running ipwatcher"
        cd /data/project/ipwatcher
        exec python www/python/src/monitor.py
        ;;
    stop)
        echo "Stopping ipwatcher"
        kubectl delete deployment ipwatcher.bot
        ;;
    restart)
        echo "Restarting ipwatcher"
        $0 stop &&
        $0 start
        ;;
    status)
        echo "Active pods:"
        kubectl get pods -l name=ipwatcher.bot
	;;
    tail)
        exec kubectl logs -f $(_get_pod)
        ;;
    attach)
        echo "Attaching"
        exec kubectl exec -i -t $(_get_pod) /bin/bash
	;;
esac
exit 0
