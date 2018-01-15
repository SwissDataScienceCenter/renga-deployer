KUBECTL_VERSION ?= 1.6.4

ci-setup-kubectl:
	curl -Lo kubectl https://storage.googleapis.com/kubernetes-release/release/$(KUBECTL_VERSION)/bin/linux/amd64/kubectl
	chmod +x kubectl
	sudo mv kubectl /usr/local/bin/

ci-setup-minikube: ci-setup-kubectl
	curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
	chmod +x minikube

ci-start-minikube: ci-setup-minikube
	export MINIKUBE_WANTUPDATENOTIFICATION=false
	export MINIKUBE_WANTREPORTERRORPROMPT=false
	export MINIKUBE_HOME=$$HOME
	export CHANGE_MINIKUBE_NONE_USER=true
	mkdir $$HOME/.kube || true
	touch $$HOME/.kube/config
	export KUBECONFIG=$$HOME/.kube/config
	sudo -E ./minikube start --vm-driver=none
	sleep 10
	sudo chown -R $$USER $$HOME/.kube
	sudo chgrp -R $$USER $$HOME/.kube
	sudo chown -R $$USER $$HOME/.minikube
	sudo chgrp -R $$USER $$HOME/.minikube
	sudo -E ./minikube update-context
	sudo -E ./minikube addons enable ingress

ci: ci-start-minikube
