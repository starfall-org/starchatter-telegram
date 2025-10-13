FROM python

RUN useradd -m -s /bin/bashn -u 1000 user

WORKDIR /home/user

USER user

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

CMD python health.py & python app/main.py