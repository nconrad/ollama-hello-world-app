import argparse
import ollama
import json
from typing import List, Dict, Optional
from waggle.plugin import Plugin
from waggle.data.vision import Camera
import logging
import os
import base64
from urllib.parse import urlparse


def get_image_data(image_uri: str) -> bytes:
    scheme = urlparse(image_uri).scheme
    if scheme in ["http", "https"]:
        return get_image_data_http(image_uri)
    if scheme == "rtsp":
        return get_image_data_stream(image_uri)
    return get_image_data_file(image_uri)


def get_image_data_http(image_uri: str) -> bytes:
    from urllib.request import urlopen
    from http.client import HTTPResponse
    from http import HTTPStatus

    with urlopen(image_uri, timeout=30) as resp:
        resp: HTTPResponse
        if resp.status != HTTPStatus.OK:
            raise FileNotFoundError(f"Unable to fetch image from URL: {image_uri}")
        return resp.read()


def get_image_data_file(image_uri: str) -> bytes:
    with open(image_uri, "rb") as f:
        return f.read()


def get_image_data_stream(stream_uri: str) -> bytes:
    """Capture one frame from an RTSP stream using pywaggle Camera and return image bytes."""
    from io import BytesIO

    with Camera(stream_uri) as camera:
        for snapshot in camera.stream():
            # Encode snapshot to JPEG bytes
            image_bytes = BytesIO()
            snapshot.save(image_bytes)
            return image_bytes.getvalue()


def run(plugin: Plugin, host: str, model: str, prompt: str, images: List[str], stream_names: Optional[Dict[str, str]] = None, publish_image: bool = False):
    logging.info("Running: model=%r and prompt=%r", model, prompt)

    client = ollama.Client(host=host)

    logging.info("Ensuring model %r has been pulled.", model)
    client.pull(model)

    if stream_names is None:
        stream_names = {}

    for image in images:
        logging.info("Processing image: %s", image)

        raw_image_data = get_image_data(image)
        logging.info("Image fetch successful, size: %d bytes", len(raw_image_data))
        encoded_image_data = base64.b64encode(raw_image_data).decode()

        # Run model on example.
        response = client.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [encoded_image_data],
                },
            ],
        )
        logging.info("Model response received")

        # Build output data.
        output = {
            "created_at": response.created_at,
            "load_duration": response.load_duration / 1e9,
            "prompt_eval_count": response.prompt_eval_count,
            # convert from nanoseconds to seconds
            "prompt_eval_duration": response.prompt_eval_duration / 1e9,
            "eval_count": response.eval_count,
            # convert from nanoseconds to seconds
            "eval_duration": response.eval_duration / 1e9,
            "model": response.model,
            "output": response.message.content,
            "input": str(image),
            "prompt": prompt,
        }

        output_json = json.dumps(output, separators=(",", ":"), sort_keys=True)

        logging.info("Publishing results: %s", output_json)
        plugin.publish("ollama_response", output_json)

        # Publish the image if requested and it came from a stream.
        if publish_image and image in stream_names:
            stream_name = stream_names[image]
            meta = {"camera": stream_name}
            plugin.upload_file(image, meta=meta)
            logging.info("Published image from stream %s", stream_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug", action="store_true", help="enable debug level logging"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("OLLAMA_HOST", "ollama.default.svc.cluster.local"),
        help="ollama host",
    )
    parser.add_argument("-m", "--model", default="gemma3", help="model to use")
    parser.add_argument(
        "-p", "--prompt", default="Describe this image.", help="prompt to use"
    )
    parser.add_argument(
        "--stream",
        dest="stream",
        action="append",
        help="stream URI (e.g., rtsp://...) to process. Multiple streams can be specified (untested).",
    )
    parser.add_argument(
        "--name",
        dest="name",
        action="append",
        help="(optional) name for the stream. Count should match --stream if provided.",
    )
    parser.add_argument(
        "--publish-image",
        action="store_true",
        help="publish captured stream images to Beehive after processing",
    )
    parser.add_argument("images", nargs="*", help="images to process")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    images = list(args.images)
    stream_names = {}

    # Handle streams if provided.
    if args.stream:
        stream_list = args.stream if isinstance(args.stream, list) else [args.stream]
        name_list = args.name if args.name else []

        for i, stream_uri in enumerate(stream_list):
            stream_name = name_list[i] if i < len(name_list) else stream_uri
            logging.info("Capturing frame from stream %s (name: %s)", stream_uri, stream_name)
            images.append(stream_uri)
            stream_names[stream_uri] = stream_name

    if not images:
        parser.error("Provide at least one image path or use --stream")

    with Plugin() as plugin:
        run(
            plugin=plugin,
            host=args.host,
            model=args.model,
            prompt=args.prompt,
            images=images,
            stream_names=stream_names,
            publish_image=args.publish_image,
        )
