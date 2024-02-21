#!/usr/bin/env bash

file="./alk.py"
config_file=".alk.yaml"
dest="/home/$USER/.local/bin"
dest_file="alk"
flag="-v"

cp $flag $file "$dest$dest_file"
