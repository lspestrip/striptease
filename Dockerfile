############################################################
# Dockerfile to build LSPE-STRIP control software environment
# Based on ubuntu:18.04
############################################################

# set base image to Ubuntu 19.04
FROM ubuntu:19.04

#install needed packages

RUN apt-get update && apt-get install --assume-yes\
    python3-pip\
    qtbase5-dev\
    qt5-default\
    libqt5charts5-dev\
    libboost-all-dev\
    libssl-dev

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

RUN useradd -M  -s /bin/bash user