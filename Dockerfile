FROM linuxserver/webtop:ubuntu-mate

RUN apt-get update && apt-get install -y python3 python3-pip python3-pyqt5
RUN pip3 install reportlab pandas

COPY . /app
WORKDIR /app

# Print logs directly to container stdout
RUN echo '#!/bin/bash\nexport DISPLAY=:1\ncd /app\npython3 /app/gajanan_clinic_app.py' > /defaults/autostart/start_app.sh && \
    chmod +x /defaults/autostart/start_app.sh