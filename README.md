# Django E-Commerce Project

A dynamic e-commerce website built with Django.

## Setup Instructions

### 1. Activate Virtual Environment

**PowerShell:**
```powershell
venv\Scripts\Activate.ps1
```

**Command Prompt:**
```cmd
venv\Scripts\activate.bat
```

### 2. Install Dependencies (if needed)
```bash
pip install -r requirements.txt
```

### 3. Run the Development Server
```bash
python manage.py runserver
```

### 4. Access the Site
Open your browser and navigate to: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

## Project Structure
- `ecommerce_project/` - Django project settings
- `store/` - Main application
  - `templates/store/` - HTML templates
  - `static/store/` - Static files (CSS, JS, images)
  - `views.py` - View functions
  - `urls.py` - URL routing

## Available Pages
- **Home** (`/`) - Landing page with featured products
- **Products** (`/category/`) - Product listing page
- **Product Detail** (`/product/`) - Individual product page
- **Cart** (`/cart/`) - Shopping cart
- **Login** (`/login/`) - User authentication

## Notes
- The project uses Django 6.0
- Static files are served from `store/static/store/`
- Templates use Django template language with `{% static %}` and `{% url %}` tags
