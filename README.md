# PriceTag 🏷️

PriceTag is a smart, real-time price tracking application designed to help you save money on your online purchases. It monitors product prices on major e-commerce platforms like Flipkart and Amazon, notifying you when prices drop below your target.

## 🚀 Features

- **Multi-Platform Support**: Track products from Flipkart and Amazon.
- **Real-Time Tracking**: Automatically updates prices to ensure you have the latest data.
- **Price History Charts**: Visualize price trends over time with interactive charts.
- **Smart Deal Scoring**: Get an instant "Deal Score" (0-100) to know if it's a good time to buy.
- **Price Drop Alerts**: Receive email notifications when a product hits your target price.
- **Price Comparison**: Automatically find better deals for the same product across different sellers/platforms.
- **Dark Mode**: Sleek, modern UI with full dark mode support.

## 🛠️ Tech Stack

- **Backend**: Django (Python)
- **Database**: SQLite
- **Frontend**: HTML5, TailwindCSS, JavaScript
- **Scraping**: BeautifulSoup4, Requests

## 📦 Installation

1. **Clone the repository**

   cd Price-Tag
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

4. **Create a superuser (optional, for admin access)**
   ```bash
   python manage.py createsuperuser
   ```

5. **Run the development server**
   ```bash
   python manage.py runserver
   ```

6. **Access the application**
   Open your browser and go to `http://127.0.0.1:8000/`

## 📖 Usage

1. **Sign Up/Login**: Create an account to start tracking your personal wishlist.
2. **Add a Product**:
   - Copy the URL of a product from Flipkart or Amazon.
   - Paste it into the "Add Product" section on your dashboard.
   - Set your desired **Target Price**.
3. **Track**: The dashboard will show the current price, lowest recorded price, and deal score.
4. **Compare**: Click "Check Price" or view details to see if the product is cheaper elsewhere.
5. **Relax**: Wait for an email notification when the price drops!

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
