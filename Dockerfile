############################################################
# Dockerfile to build LSPE-STRIP control software environment
# Based on ubuntu:20.04
############################################################

# set base image to Ubuntu 20.04
FROM ubuntu:20.04

#install needed packages

ENV TZ=Europe/Rome
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get update && apt-get install --assume-yes\
    python3-pip\
    qtbase5-dev\
    qt5-default\
    libqt5charts5-dev\
    libboost-all-dev\
    libssl-dev\
    python3-scipy

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

RUN useradd -M  -s /bin/bash user
