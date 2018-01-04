#!/bin/bash
gifsicle --delay=10 --loop images/*.gif > gifsicle_anim.gif
convert -delay 10 -loop 0 images/*.gif convert_anim.gif
