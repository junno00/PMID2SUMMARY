FROM python:3.12

WORKDIR /home
ENV PYTHONBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    locales curl less vim && \
    localedef -f UTF-8 -i ja_JP ja_JP.UTF-8 && \
    pip install --upgrade pip && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    export PATH="/root/.local/bin:$PATH" && \
    poetry config virtualenvs.create false && \
    poetry config virtualenvs.in-project true

ENV LANG=ja_JP.UTF-8
ENV LANGUAGE=ja_JP:ja
ENV LC_ALL=ja_JP.UTF-8
ENV TZ=JST-9
ENV TERM=xterm
ENV PATH="/root/.local/bin:$PATH"
RUN echo 'export PATH="/root/.local/bin:$PATH"' > /etc/profile.d/poetry.sh
