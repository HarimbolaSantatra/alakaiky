#!/usr/bin/env bash

file="./alk"
config_file=".alk.yaml"
dest="/home/$USER/.local/bin"
flag="-v"


if [ ! -e $config_file ]; then
    echo "$config_file doesn't exist!"
fi

cp $flag $file "$dest"
