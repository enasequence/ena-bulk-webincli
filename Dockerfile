FROM ubuntu:18.04
RUN apt update && apt --assume-yes install python3.6
RUN apt-get install -y python3-pandas
COPY read_validator.py read_validator.py
VOLUME /tmp
ENTRYPOINT ["python3", "read_validator.py"]