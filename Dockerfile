# 1. Hangi işletim sistemi ve Python sürümü kullanılacak? (Hafif ve hızlı bir sürüm)
FROM python:3.11-slim

# 2. Konteyner içindeki çalışma klasörümüzü belirliyoruz
WORKDIR /app

# 3. Kütüphane listesini konteynere kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Projenin kaynak kodlarını ve model dosyasını kopyala
COPY src/ ./src/
COPY models/ ./models/
# Not: Eğer makine öğrenmesi modelin (örneğin rf_model.pkl) ana dizindeyse onu da kopyalamalıyız.
COPY *.pkl . 

# 5. Dışarıya açılacak port
EXPOSE 8000

# 6. Uygulamayı başlatma komutu
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]