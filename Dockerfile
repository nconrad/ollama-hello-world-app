FROM waggle/plugin-base:1.1.1-base

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY . .

ENTRYPOINT [ "python3", "main.py" ]
