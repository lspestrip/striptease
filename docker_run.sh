docker run -ti -e DISPLAY\
       -v /tmp/.X11-unix:/tmp/.X11-unix\
       -v $HOME/:/home/user/:rw\
       -u user\
       --net=host strip/striptease bash
