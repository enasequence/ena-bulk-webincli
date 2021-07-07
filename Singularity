Bootstrap: docker
From: ubuntu:18.04
Stage: build

%setup
    # Install packages
    apt update && apt install -y curl wget default-jre && apt --assume-yes install python3.6
    apt-get install -y python3-pandas && apt-get install -y python3-joblib

%files
    bulk_webincli.py bulk_webincli.py

%post
    # Install script and software dependencies
    echo "Downloading latest Webin-CLI..."
    curl -s https://api.github.com/repos/enasequence/webin-cli/releases/latest | grep "browser_download_url" | cut -d : -f 2,3 | tr -d \" | wget -qi -
    mv webin-cli-* webin-cli.jar
    echo "Downloading latest Webin-CLI... [COMPLETE]"
    chmod 554 bulk_webincli.py && chmod 554 webin-cli.jar

# Set working directory to volume where data is housed
# WORKDIR /data

%runscript
    echo "Arguments received: $*"
    exec python3 /bulk_webincli.py "$@"