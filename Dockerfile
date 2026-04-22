FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

ARG JULIA_VERSION=1.10.4

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl tar xz-utils \
    && arch="$(dpkg --print-architecture)" \
    && case "$arch" in \
        amd64) julia_url_arch="x64"; julia_file_arch="x86_64" ;; \
        arm64) julia_url_arch="aarch64"; julia_file_arch="aarch64" ;; \
        *) echo "Unsupported architecture for Julia: $arch"; exit 1 ;; \
    esac \
    && julia_series="${JULIA_VERSION%.*}" \
    && julia_tarball="julia-${JULIA_VERSION}-linux-${julia_file_arch}.tar.gz" \
    && julia_url="https://julialang-s3.julialang.org/bin/linux/${julia_url_arch}/${julia_series}/${julia_tarball}" \
    && curl -fsSL "$julia_url" -o "/tmp/${julia_tarball}" \
    && tar -xzf "/tmp/${julia_tarball}" -C /opt \
    && ln -s "/opt/julia-${JULIA_VERSION}/bin/julia" /usr/local/bin/julia \
    && rm -f "/tmp/${julia_tarball}" \
    && apt-get purge -y --auto-remove curl tar xz-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["python", "-m", "lifeos.cli", "--setup"]
