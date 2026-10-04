FROM linuxserver/webtop:ubuntu-mate

# Dependencies install kara
RUN apt-get update && apt-get install -y python3 python3-pip python3-pyqt5
RUN pip3 install reportlab pandas

# Application files copy kara
COPY . /app
WORKDIR /app

# MATE Desktop session autostart configuration
RUN mkdir -p /config/.config/autostart
RUN echo '[Desktop Entry]\n\
Type=Application\n\
Exec=python3 /app/gajanan_clinic_app.py\n\
Hidden=false\n\
NoDisplay=false\n\
X-GNOME-Autostart-enabled=true\n\
Name=Gajanan Billing\n\
Comment=Start Gajanan Clinic Billing App' > /config/.config/autostart/gajanan.desktop

# Desktop shortcut (Manual Backup sathi)
RUN mkdir -p /config/Desktop
RUN echo '[Desktop Entry]\n\
Type=Application\n\
Exec=python3 /app/gajanan_clinic_app.py\n\
Name=Gajanan Billing\n\
Icon=utilities-terminal\n\
Terminal=false' > /config/Desktop/gajanan.desktop && chmod +x /config/Desktop/gajanan.desktop