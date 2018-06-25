FROM ros:melodic

# setup catkin workspace
ENV CATKIN_WS=/root/catkin_ws
RUN mkdir -p $CATKIN_WS/src
WORKDIR $CATKIN_WS/src

# clone source code
RUN git clone https://github.com/ruffsl/roschaos.git

# install build dependacies
RUN apt-get -qq update && \
    apt-get -qq install -y \
        python-catkin-tools && \
    rosdep update && \
    rosdep install -y \
      --from-paths . \
      --ignore-src \
      --rosdistro ${ROS_DISTRO} \
      --as-root=apt:false && \
    rm -rf /var/lib/apt/lists/*

# build from source
WORKDIR $CATKIN_WS
ENV TERM xterm
ENV PYTHONIOENCODING UTF-8
RUN catkin config \
      --extend /opt/ros/$ROS_DISTRO && \
    catkin build

# setup entrypoint
COPY ./ros_entrypoint.sh /
ENTRYPOINT ["/ros_entrypoint.sh"]
