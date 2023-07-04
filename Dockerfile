FROM python:3.10

ENV DEPLOY=1

RUN mkdir -p /opt/plana && mkdir -p /opt/tmp

WORKDIR /opt/plana

COPY . /opt/plana

RUN apt-get update
RUN apt install -y libgl1-mesa-glx ffmpeg
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

EXPOSE 80

CMD ["sh", "start.sh"]