FROM python:3.11

RUN useradd -m -s /bin/bash -u 1000 user

WORKDIR /home/user

USER user

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

EXPOSE 7860

CMD python health.py & cd app && python main.py


