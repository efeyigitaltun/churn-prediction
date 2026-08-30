FROM python:3.11-slim
WORKDIR /app

# Kütüphaneleri kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend klasörünü kopyala
COPY frontend/ ./frontend/

# Streamlit portunu dışarı aç
EXPOSE 8501

# Uygulamayı başlat
CMD ["streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0"]