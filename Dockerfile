FROM ubuntu:18.04

# Install packages
RUN apt update && apt install -y curl, wget && apt --assume-yes install python3.6
RUN apt-get install -y python3-pandas && apt-get install -y python3-joblib

# Install script and software dependencies
RUN echo "Downloading latest Webin-CLI..."
RUN curl -s https://api.github.com/repos/enasequence/webin-cli/releases/latest | grep "browser_download_url" | cut -d : -f 2,3 | tr -d \" | wget -qi -
RUN echo "Downloading latest Webin-CLI... [COMPLETE]"
COPY read_validator.py read_validator.py

VOLUME /tmp
#ENTRYPOINT ['python3', 'read_validator.py']