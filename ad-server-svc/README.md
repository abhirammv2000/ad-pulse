# AdServer
Backend code for the Ad-Server SVC.

## Steps to setup the project locally
Excecute the commands sequentially in order to successfully run the application locally on a Mac OS. For a different OS use the links that follow

### Install Golang
```
brew install golang

go version
```

### Different OS
```
Golang - https://go.dev/doc/install

```

### Install other required packages
```
brew install golang-migrate

go install -v github.com/golang/mock/mockgen@v1.6.0
```

### Different OS
```
Golang migrate - https://github.com/golang-migrate/migrate

Mockgen - https://github.com/golang/mock

```

### Add PATH to shell
- open your .zshrc or .bashrc file.
- add - export PATH=$PATH:~/go/bin
- save and close the file
- open terminal and excute 
```
source ~/.zshrc
```

### Run the server
```
make server
```

### Build Docker image
```
docker build -t adserver-svc .
```

### Run as Docker container
```
docker run \
      --name advserver-svc \
      --rm -it \
      -v /:/host:ro \
      -v /var/run/docker.sock:/var/run/docker.sock:ro \
      --privileged \
      --pid=host \
      --network=host \
      adserver-svc:latest
```





