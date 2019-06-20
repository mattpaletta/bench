FROM python:3.6
WORKDIR /
COPY requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt
COPY merge.py /merge.py
ENTRYPOINT ["python3", "merge.py"]
