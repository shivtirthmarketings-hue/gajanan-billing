FROM linuxserver/webtop:ubuntu-mate

# Dependencies install kara
RUN apt-get update && apt-get install -y python3 python3-pip python3-pyqt5
RUN pip3 install reportlab pandas

# Application files copy kara
COPY . /app
WORKDIR /app

# S6 Init script banva jya dware GUI startup la app run hoil
RUN mkdir -p /custom-cont-init.d && \
    echo '#!/bin/bash\n\
sleep 5\n\
export DISPLAY=:1\n\
python3 /app/gajanan_clinic_app.py &' > /custom-cont-init.d/start_app.sh && \
    chmod +x /custom-cont-init.d/start_app.sh