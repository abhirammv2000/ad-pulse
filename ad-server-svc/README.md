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





