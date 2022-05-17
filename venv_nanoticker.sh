#!/bin/sh

#Script to create and delete a virtualenv to keep dependencies separate from other projects 
# ./venv_nanoticker.sh create 
 # ./venv_nanoticker.sh delete

action=$1

if [ "$action" = "" ]; 
then
    pip3 install virtualenv --quiet
    python3 -m venv venv_nanoticker
    . venv_nanoticker/bin/activate

    pip3 install -r ./config/requirements.txt --quiet

    echo "A new virstaul environment was created. "
    
    
elif [ "$action" = "delete" ];
then 
    . venv_nanoticker/bin/activate
    deactivate    
    rm -rf venv_nanoticker

else
     echo "run ./venv_nanoticker.sh  to create a virtual python environment"
     echo "or"
     echo "run ./venv_nanoticker.sh delete  to delete the virstual python environment"
fi


