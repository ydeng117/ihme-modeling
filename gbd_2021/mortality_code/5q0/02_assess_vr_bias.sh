#! /bin/bash

code_path=$1
conda_path=$2
conda_env=$3
version_id=$4

eval "${conda_path}/envs/${conda_env}/bin/python ${code_path} --version_id ${version_id}"