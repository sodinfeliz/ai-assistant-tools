FROM python:3.8.8

LABEL maintainer="elliotsu@geosat.com.tw"
ENV DEBIAN_FRONTEND=noninetractive

# Environment setting
RUN apt-get update && apt-get install -y software-properties-common
RUN apt-add-repository ppa:ubuntugis/ppa
RUN apt-get install -y build-essential python-opencv gdal-bin libgdal-dev vim net-tools qt5-default

RUN wget http://ftp.br.debian.org/debian/pool/main/x/xcb-util/libxcb-util1_0.4.0-1+b1_amd64.deb
RUN dpkg -i ./libxcb-util1_0.4.0-1+b1_amd64.deb 

# Install the Python dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

CMD ["python", "main.py"]