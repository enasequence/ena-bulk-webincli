FROM ubuntu:18.04

# Install packages
RUN apt update && apt install -y curl wget default-jre && apt --assume-yes install python3.6
RUN apt-get install -y python3-pandas && apt-get install -y python3-joblib

# Install script and software dependencies
RUN echo "Downloading latest Webin-CLI..."
RUN curl -s https://api.github.com/repos/enasequence/webin-cli/releases/latest | grep "browser_download_url" | cut -d : -f 2,3 | tr -d \" | wget -qi -
RUN mv webin-cli-* webin-cli.jar
RUN echo "Downloading latest Webin-CLI... [COMPLETE]"

COPY bulk_webincli.py bulk_webincli.py
RUN chmod 554 bulk_webincli.py && chmod 554 webin-cli.jar

# Set working directory to volume where data is housed
WORKDIR /data

ENTRYPOINT ["python3", "/bulk_webincli.py"]