# Deploy

## Deploy with Docker
Deploying with Docker is great. **But you cannot use this in macOS and Windows**. Since the containers are actually running in a virtual machine instead of your host computer, there will be some problem with networking.

### Build
```bash
docker build -t fr0der1c/everyclass-server .
```

### Run
```bash
docker run -it --rm -d \
    --net=host \
    --name "everyclass-`git describe`" \
    -v "`pwd`/everyclass/config:/var/everyclass-server/config" \
    -v "`pwd`/calendar_files:/var/everyclass-server/calendar_files" \
    -e UWSGI_HTTP_SOCKET=":9000" \
    fr0der1c/everyclass-server
```

Passing environment variable `-e UWSGI_HTTP_SOCKET=":9000"` when running `docker run` to change port.