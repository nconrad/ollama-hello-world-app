# Ollama "Hello World" App

This app allow you to run a simple prompt against a set of examples images using Ollama.

It is primarily useful for understanding and testing the basic pipeline of getting an image to Ollama, confirming that the runtime is working, and publishing results back to Beehive.

## Usage

The app takes the following arguments:

* `--debug`: Enable debug level logging.
* `--host`: Specify Ollama runtime host. (Default is `ollama` for WES compatibility. Can also provide using `OLLAMA_HOST` environment variable.)
* `-m / --model`: Model to process images with.
* `-p / --prompt`: Prompt to process images with.
* `--stream`: Stream URI (e.g., `rtsp://...`) to capture and process. Multiple streams can be specified _(but this is untested)_.
* `--name`: (optional) Name for the stream. Count should match the number of `--stream` arguments.
* `--publish-image`: Publish captured stream images to Beehive after processing.

The remainder of the arguments are paths to images that will be processed.

As a complete example, we ask a simple question about [one of the example images](./examples/animal.jpg):

```
python3 main.py --model gemma3 --prompt "Are there any animals in this image?" examples/animal.jpg
```

To process a frame from an RTSP camera stream:

```
python3 main.py --stream rtsp://10.31.81.27:554/profile1/media.smp --name lab_ptz --model gemma3 --prompt "Describe this image."
```

To process a stream and publish the image to Beehive:

```
python3 main.py --stream rtsp://10.31.81.27:554/profile1/media.smp --name lab_ptz --publish-image --model gemma3 --prompt "Describe this image."
```