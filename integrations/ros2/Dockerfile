FROM ros:jazzy-ros-base@sha256:066420e07f60aa18262f2479981def87ebcfcec42eefb0c0c57c4a46098348ca AS ros-base
SHELL ["/bin/bash", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-gz-sim-vendor ros-jazzy-simulation-interfaces \
    python3-colcon-common-extensions python3-venv build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace

FROM ros-base AS integration
COPY integrations/ros2/simweave_gazebo /opt/simweave_ws/src/simweave_gazebo
WORKDIR /opt/simweave_ws
RUN source /opt/ros/jazzy/setup.bash && \
    colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release --parallel-workers 1
RUN python3 -m venv --system-site-packages /opt/simweave_venv && \
    /opt/simweave_venv/bin/pip install --no-cache-dir uv==0.11.16
ENV VIRTUAL_ENV=/opt/simweave_venv
ENV PATH=/opt/simweave_venv/bin:$PATH
ENV UV_PROJECT_ENVIRONMENT=/opt/simweave_venv
ENV ROS_LOCALHOST_ONLY=1
ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
WORKDIR /workspace
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --active --extra dev --extra mujoco
COPY tests ./tests
COPY integrations/ros2/tests ./integrations/ros2/tests
COPY examples ./examples
COPY integrations/ros2/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && useradd --create-home --uid 10001 runner && \
    chown -R runner:runner /workspace
USER runner
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "pytest", "integrations/ros2/tests", "-v", "--tb=short"]
