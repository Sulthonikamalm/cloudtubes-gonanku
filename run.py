from app import buat_aplikasi

# Objek aplikasi untuk dev server (flask run) dan gunicorn (run:app).
app = buat_aplikasi()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
