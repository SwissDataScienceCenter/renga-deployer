ci-setup-minikube:
	curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
	chmod +x minikube
	./minikube version
	./minikube config set WantReportErrorPrompt false

ci-start-minikube: ci-setup-minikube
	./minikube start

ci: ci-start-minikube
