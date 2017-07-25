ci-setup-kubectl:
	curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/darwin/amd64/kubectl
	chmod +x kubectl
	sudo mv kubectl /usr/local/bin/

ci-setup-minikube: ci-setup-kubectl
	curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
	chmod +x minikube
	./minikube version
	./minikube config set WantReportErrorPrompt false

ci-start-minikube: ci-setup-minikube
	./minikube start --v=3 --vm-driver=none --use-vendored-driver

ci: ci-start-minikube
