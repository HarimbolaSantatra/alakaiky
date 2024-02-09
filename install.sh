#!/usr/bin/env bash

file="./alakaiky"
config_file="config.yaml"
config_path="$HOME/.local/state/alakaiky"
dest="/home/$USER/.local/bin"
flag="-v"

mkdir -p "$config_path"

if [ ! -e $config_file ]; then
    echo "$config_file doesn't exist!"
else
    cp $config_file "$config_path"
fi

cp $flag $file "$dest"