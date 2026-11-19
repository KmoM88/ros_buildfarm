RUN find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i -e 's|http://archive.ubuntu.com/ubuntu|http://us-central1.gce.archive.ubuntu.com/ubuntu|g' -e 's|http://security.ubuntu.com/ubuntu|http://us-central1.gce.archive.ubuntu.com/ubuntu|g' {} + && printf 'Acquire::ForceIPv4 "true";\nAcquire::Retries "3";\nAcquire::http::Timeout "15";\n' > /etc/apt/apt.conf.d/99rosbf-fast-mirror
RUN for i in 1 2 3; do apt-get update && apt-get install -q -y locales && apt-get clean && break || if [ $i -lt 3 ]; then sleep 5; else false; fi; done
RUN echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV TZ @timezone
