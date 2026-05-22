FROM mcr.microsoft.com/devcontainers/base:noble

# SSH server
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server curl ca-certificates \
    && mkdir -p /var/run/sshd \
    && ssh-keygen -A \
    && sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/UsePAM yes/UsePAM no/' /etc/ssh/sshd_config \
    && echo "Port 2222" >> /etc/ssh/sshd_config \
    && echo 'vscode:vscode' | chpasswd \
    && passwd -u vscode \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# SSH public key
RUN mkdir -p /home/vscode/.ssh && chmod 700 /home/vscode/.ssh \
    && echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCqelad5JZKQFekjAIIUM0CquefQbRlDvUIuAL2Lja3/T1JYFcLASULWg7b0hnFuRgO+GlzxHiDQ0af9dcEEAkJyeyl3uMdr2MaupMx47Ul/ErKVshVaLwREG5zCS8D3OBB1/QygdtfJzbRB/xcxGhBtXxlH2epXf2GfsSUVMI2VFjQIm1JRReZ/EXO1twTEJA/ArSpZhWWCY933yvpkGLL4+TvlfX4ZaV+9UrWchDlwd/MUixO7xoMy4MwofazYeB5EUgZ8VM8tEKl49ldGV0ASim3MiZK/9fwlnBDIoXGV+Gc22kmm1IghyQ3dOIFToyD8LragMO+jDJceuk53J/4pPxc3vcbxEguKJJtOePtZK0e41vkNz868YXEmAb6yUC4l2OXYxBbmYCjmcpzrjHoRrA115OpOM7e3X384YTrcWD4NiMMdJ+bIH2ubYnr+yXDDixwvgIx964My7f0gj2Pqgi7jwq3XSKfhJil64PkjeOe1uz0Ae+d6rnHJUCZ7u0= dsun@HP-DESKTOP" > /home/vscode/.ssh/authorized_keys \
    && chmod 600 /home/vscode/.ssh/authorized_keys \
    && chown -R vscode:vscode /home/vscode/.ssh

# Node.js (for npx)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

EXPOSE 2222
