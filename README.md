# Photo Sorting App (MVP)

This project is a multiuser photo sorting app built with **Flask**, **SQLAlchemy**, and **SQLite**.  
Users can upload photos, define categories, and let the app automatically categorize photos using **OpenAI image and text analysis**.  

---

## ⚡ Features

- User Management: signup, login/logout, delete account
- Photo Management: upload, update, delete, view
- Category Management: add, update, delete
- AI-assisted categorization via OpenAI

## 📂 Project Structure

photo_sorter/  
├── app.py              # App factory + blueprint registration  
├── config.py             # Config for Flask (DB URI, SECRET_KEY, UPLOAD_FOLDER)  
├── requirements.txt    # Python dependencies  
├── README.md           # Project documentation  
├── models.py           # SQLAlchemy models  
├── data_manager.py     # database access layer / DataManager class  
├── .env                # Environment variables (API keys, secrets)  
└── packages/  
    ├── templates/      # Jinja2 HTML templates  
    │  ├─ base.html  
    │  ├─ index.html  
    │  ├─ dashboard.html  
    │  └── edit_profile.html  
    ├── static/         # CSS  
    │  ├─ uploads/      # Uploaded photos (default storage folder, configurable via UPLOAD_FOLDER in .env)  
    │  └── style.css  
    ├── services/       # Business logic (OpenAI, image handling, etc.)  
    │  ├─ openai_service.py      # OpenAI sorting logic  
    │  └── photo_service.py      # photo-specific utilities (resize, file path, etc.)  
    ├── routes/         # Flask Blueprints  
    │  ├─ auth.py           # login, logout  
    │  ├─ photos.py         # upload, list, update, delete  
    │  ├─ user.py           # signup, update, delete  
    │  └── categories.py     # add, list, update, delete   
    └── data/           # Local storage  
 

## 🛠 Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/andrea-py-ai/Photo-Sorter.git  
   ```
   
2. **Create a virtual environment & activate it**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux / Mac
   venv\Scripts\activate      # Windows
   ```

3. **Install dependencies**
    ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**  
Copy .env.example → .env
Add your OpenAI API key and other secrets:
    ```env
   SECRET_KEY=supersecret
   OPENAI_API_KEY=your_openai_key_here
   UPLOAD_FOLDER=static/uploads # folder where uploaded photos will be stored  
   LOG_LEVEL=INFO
   ```
   
Note:  
- Uploaded photos are stored in UPLOAD_FOLDER (default: static/uploads).    
Make sure this folder exists or is writable. 
- By default, the SQLite database is stored at packages/data/photos.db.

5. **Run the app**
    ```bash
   flask run
   ```
Then visit http://127.0.0.1:5002/ in your browser.  