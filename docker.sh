#!/bin/bash

sudo docker build --no-cache -t jpra1113/snap:xenial .
sudo docker push jpra1113/snap:xenial
