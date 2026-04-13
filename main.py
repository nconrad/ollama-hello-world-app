import argparse
import ollama
import json
from waggle.plugin import Plugin
import logging
import os
import base64
import subprocess
from urllib.parse import urlparse


LAB_CAMERA_RTSP_URL = "rtsp://sage:MySageCamera@10.31.81.27:554/profile2/media.smp"


def get_image_data(image_uri: str) -> bytes:
    scheme = urlparse(image_uri).scheme
    if scheme in ["http", "https"]:
        return get_image_data_http(image_uri)
    if scheme == "rtsp":
        return get_image_data_rtsp(image_uri)
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


def get_image_data_rtsp(image_uri: str) -> bytes:
    """Capture one frame from an RTSP camera URL using ffmpeg and return image bytes."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-rtsp_transport",
            "tcp",
            "-i", image_uri,
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "-",
        ],
        capture_output=True,
        timeout=10,
    )
    if result.returncode != 0 or not result.stdout:
        ffmpeg_err = result.stderr.decode(errors="replace")
        raise RuntimeError(f"ffmpeg failed: {ffmpeg_err}")
    return result.stdout


def run(plugin: Plugin, host: str, model: str, prompt: str, images: list[str]):
    logging.info("Running: model=%r and prompt=%r", model, prompt)

    client = ollama.Client(host=host)

    logging.info("Ensuring model %r has been pulled.", model)
    client.pull(model)

    for image in images:
        logging.info("Processing image: %s", image)

        raw_image_data = get_image_data(image)
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
        "--use-lab-camera",
        action="store_true",
        help="capture one frame from the lab RTSP camera and process it",
    )
    parser.add_argument("images", nargs="*", help="images to process")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    images = list(args.images)

    if args.use_lab_camera:
        images.append(LAB_CAMERA_RTSP_URL)

    if not images:
        parser.error("Provide at least one image path or pass --use-lab-camera")

    with Plugin() as plugin:
        run(
            plugin=plugin,
            host=args.host,
            model=args.model,
            prompt=args.prompt,
            images=images,
        )
