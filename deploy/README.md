# Deploy

## Deploy with Docker
Deploying with Docker is great. **But due to Docker networking problem, you cannot use this in macOS and Windows**.

### With script
There is a script to simplify deploying. The command below would build the image, start a new container and remove old containers.
```bash
bash upgrade.sh
```

If you don't want to build image, use `--no-build` flag to use your pre-built image.

### Directly with Docker
Also it's possible to directly interact with Docker. Use these commands instead.

#### Build
```bash
docker build -t fr0der1c/everyclass-server .
```

#### Run
```bash
docker run -it --rm -d \
    --net=host \
    --name "everyclass-`git describe --tags`-`date "+%m%d-%H%M"`" \
    -v "`pwd`/everyclass/server/config:/var/everyclass-server/everyclass/server/config" \
    -v "`pwd`/calendar_files:/var/everyclass-server/calendar_files" \
    -p 9000:9000 \
    -e UWSGI_HTTP_SOCKET=":9000" \
    fr0der1c/everyclass-server
```

- `uwsgi` will detect environment variable `UWSGI_HTTP_SOCKET` to see which port to bind.
- The `-p 9000:9000` line is for Registrator to recognize ports of our service. If you omit this line, it may not be registered to Consul.