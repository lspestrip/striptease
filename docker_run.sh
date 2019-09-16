docker run -ti -e DISPLAY\
       -v /tmp/.X11-unix:/tmp/.X11-unix\
       -v $HOME/:/home/user/:rw\
       -v $PWD:/striptease:rw\
       -w /striptease\
       -u user\
       --privileged\
       --net=host strip/striptease bash
