# Python 공식 이미지를 기반으로 합니다.
FROM python:3.9-slim-buster

# 작업 디렉토리를 설정합니다.
WORKDIR /app

# requirements.txt를 복사하고 Python 의존성을 설치합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드를 작업 디렉토리로 복사합니다.
COPY . .

# Flask 애플리케이션을 실행할 포트를 노출합니다.
EXPOSE 5000

# Flask 애플리케이션을 실행합니다.
# Gunicorn과 같은 프로덕션용 WSGI 서버를 사용하는 것이 좋지만,
# 여기서는 개발 목적으로 Flask의 내장 서버를 사용합니다.
CMD ["python", "app.py"]