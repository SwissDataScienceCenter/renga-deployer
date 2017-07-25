ci-setup-minikube:
	curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
	chmod +x minikube
	./minikube version
	./minikube config set WantReportErrorPrompt false

ci-setup-nvm:
	nvm install 6
	nvm use 6

ci: ci-setup-nvm ci-setup-minikube
