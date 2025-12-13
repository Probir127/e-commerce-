# RB Trading - E-commerce Platform

A fully functional, responsive, and dynamic e-commerce website built with Django. This project features a modern UI, a powerful admin panel (Jazzmin), Stripe payment integration, and mobile-optimized design.

## 🚀 Features

- **Storefront**:
  - Dynamic product listings with categories and advanced filtering.
  - Responsive design (Mobile, Tablet, Desktop) with mobile navigation drawer.
  - Search functionality and pagination.
  - Product detail pages with image galleries and related products.
  - Shopping cart with AJAX updates (no page reload).
  - User authentication (Sign Up, Login, Profile, Order History).

- **Checkout & Payments**:
  - Secure checkout process.
  - **Stripe Integration** for credit card payments.
  - **Cash on Delivery (COD)** option.
  - Order tracking system with timeline view.

- **Admin Panel**:
  - Custom branded interface using `django-jazzmin`.
  - Dashboard with key metrics.
  - Visual **Stock Status Indicators** (Low Stock alerts).
  - Order management (status updates, invoicing).
  - Product management with bulk actions.

## 🛠️ Tech Stack

- **Backend**: Python, Django 5.2
- **Database**: SQLite (default)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Payment**: Stripe API
- **Admin**: Django Jazzmin

## ⚙️ Installation & Setup

Follow these steps to set up the project locally:

### 1. Clone the Repository
```bash
git clone https://github.com/Probir127/e-commerce-.git
cd e-commerce-
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# Activate on Windows:
venv\Scripts\activate
# Activate on macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory (next to `manage.py`) and add:
```env
# Security
SECRET_KEY=your-secret-key-here
DEBUG=True

# Stripe (Test Keys)
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_... (Optional)

# Email (Optional/For production)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 5. Apply Migrations
```bash
python manage.py migrate
```

### 6. Create Superuser (Admin)
```bash
python manage.py createsuperuser
```

### 7. Run the Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` to view the site.
Access the admin panel at `http://127.0.0.1:8000/admin`.

## 📱 Mobile Features
- **Swipe-friendly navigation**: Hamburger menu on mobile.
- **Back-to-top button**: Appears on scroll.
- **Optimized layouts**: Single column on phone, multi-column on desktop.
- **Touch targets**: Enhanced for mobile usage.

## 📄 License
This project is open-source and available for educational purposes.
