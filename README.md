# Ollama "Hello World" App

This app allow you to run a simple prompt against a set of examples images using Ollama.

It is primarily useful for understanding and testing the basic pipeline of getting an image to Ollama, confirming that the runtime is working, and publishing results back to Beehive.

## Usage

The app takes the following arguments:

* `--debug`: Enable debug level logging.
* `--host`: Specify Ollama runtime host. (Default is `ollama` for WES compatibility. Can also provide using `OLLAMA_HOST` environment variable.)
* `-m / --model`: Model to process images with.
* `-p / --prompt`: Prompt to process images with.
* `--use-lab-camera`: Capture one frame from the lab RTSP camera with `ffmpeg` and include it in processing.

The remainder of the arguments are paths to images that will be processes.

As a complete example, we ask a simple question about [one of the example images](./examples/animal.jpg):

```
python3 main.py --model gemma3 --prompt "Are there any animals in this image?" examples/animal.jpg
```

## Docker Notes

`ffmpeg` is installed in the Docker image, which is required for `--use-lab-camera` (RTSP frame capture).

You can verify it after building:

```bash
docker build -t ollama-hello-world:local .
docker run --rm ollama-hello-world:local ffmpeg -version
```