FROM linuxserver/webtop:ubuntu-mate

RUN apt-get update && apt-get install -y python3 python3-pip python3-pyqt5
RUN pip3 install reportlab pandas

COPY . /app
WORKDIR /app

# Display setup ani app launch command
RUN echo "export DISPLAY=:1" >> /defaults/autostart && \
    echo "python3 /app/gajanan_clinic_app.py &" >> /defaults/autostart