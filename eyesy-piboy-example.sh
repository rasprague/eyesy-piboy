#!/bin/bash
DEVICE="default"
RATE=44100
DOUBLEBUF=1
CONTROLLER_MAPPING="piboy-mapping.py"

pushd /home/pi/Eyesy
./start_python_foreground.sh --device $DEVICE --rate $RATE --double-buffer $DOUBLEBUF --controller-mapping $CONTROLLER_MAPPING
popd
