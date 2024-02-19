#!/usr/bin/env bash

file="./alk"
config_file=".alk.yaml"
dest="/home/$USER/.local/bin"
flag="-v"

cp $flag $file "$dest"
