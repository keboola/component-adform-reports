FROM python:3.8.6-slim
ENV PYTHONIOENCODING=utf-8

COPY requirements.txt /code/requirements.txt
COPY flake8.cfg /code/flake8.cfg

RUN pip install flake8

RUN pip install -r /code/requirements.txt

COPY . /code/
WORKDIR /code/

CMD ["python", "-u", "/code/src/component.py"]
