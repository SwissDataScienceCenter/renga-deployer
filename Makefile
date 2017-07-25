ci-setup-kubectl:
	curl -Lo kubectl https://storage.googleapis.com/kubernetes-release/release/v1.6.4/bin/linux/amd64/kubectl
	chmod +x kubectl
	sudo mv kubectl /usr/local/bin/

ci-setup-minikube: ci-setup-kubectl
	curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
	chmod +x minikube
	./minikube version
	./minikube config set WantReportErrorPrompt false

ci-start-minikube: ci-setup-minikube
	./minikube start --show-libmachine-logs --vm-driver=none --use-vendored-driver

ci: ci-start-minikube
