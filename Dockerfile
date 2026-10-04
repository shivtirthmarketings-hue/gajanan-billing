FROM linuxserver/webtop:ubuntu-mate

# Dependencies install kara
RUN apt-get update && apt-get install -y python3 python3-pip python3-pyqt5
RUN pip3 install reportlab pandas

# Application files copy kara
COPY . /app
WORKDIR /app

# 1. Custom S6 Service Setup
RUN mkdir -p /custom-services.d
RUN echo '#!/usr/bin/with-contenv bash\n\
exec s6-setuidgid abc bash -c "sleep 8 && export DISPLAY=:1 && cd /app && python3 /app/gajanan_clinic_app.py"' > /custom-services.d/gajanan-app && \
    chmod +x /custom-services.d/gajanan-app

# 2. Backup Desktop Autostart Shortcut
RUN mkdir -p /config/.config/autostart
RUN echo '[Desktop Entry]\n\
Type=Application\n\
Exec=bash -c "sleep 5 && export DISPLAY=:1 && cd /app && python3 /app/gajanan_clinic_app.py"\n\
Hidden=false\n\
NoDisplay=false\n\
X-GNOME-Autostart-enabled=true\n\
Name=Gajanan Billing' > /config/.config/autostart/gajanan.desktop