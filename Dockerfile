FROM linuxserver/webtop:ubuntu-mate

# Install python and dependencies
RUN apt-get update && apt-get install -y python3 python3-pip python3-pyqt5
RUN pip3 install reportlab pandas

# Copy application files
COPY . /app
WORKDIR /app

# Desktop shortcut & Startup script setup
RUN mkdir -p /config/Desktop /config/.config/autostart
RUN echo '#!/bin/sh\nexport DISPLAY=:1\npython3 /app/gajanan_clinic_app.py' > /app/start_app.sh && chmod +x /app/start_app.sh

# Create Desktop Shortcut
RUN echo '[Desktop Entry]\nType=Application\nName=Gajanan Billing\nExec=/app/start_app.sh\nIcon=utilities-terminal\nTerminal=true' > /config/Desktop/GajananBilling.desktop && chmod +x /config/Desktop/GajananBilling.desktop

# Create Autostart Entry
RUN echo '[Desktop Entry]\nType=Application\nName=Gajanan Billing\nExec=/app/start_app.sh' > /config/.config/autostart/GajananBilling.desktop