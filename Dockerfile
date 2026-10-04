FROM linuxserver/webtop:ubuntu-mate

# Install dependencies
RUN apt-get update && apt-get install -y python3 python3-pip python3-pyqt5
RUN pip3 install reportlab pandas

# Copy application files
COPY . /app
WORKDIR /app

# Autostart script
RUN mkdir -p /defaults/autostart
RUN echo '#!/bin/bash\nexport DISPLAY=:1\ncd /app\npython3 /app/gajanan_clinic_app.py > /app/app.log 2>&1 &' > /defaults/autostart/start_app.sh && \
    chmod +x /defaults/autostart/start_app.sh