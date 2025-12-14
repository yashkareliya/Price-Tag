from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Product, PriceHistory
from .scraper import get_product_details, search_products
from django.utils import timezone
from django.http import JsonResponse

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    products = Product.objects.filter(user=request.user).order_by('-created_at')
    total_items = products.count()
    deals_found = sum(1 for p in products if p.is_below_threshold)
    
    total_savings = sum(
        (p.target_price - p.current_price) 
        for p in products 
        if p.is_below_threshold and p.current_price and p.target_price
    )
    
    context = {
        'products': products,
        'total_items': total_items,
        'deals_found': deals_found,
        'total_savings': total_savings,
    }
    return render(request, 'tracker/dashboard.html', context)

def product_list(request):
    if not request.user.is_authenticated:
        return redirect('login')
    products = Product.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'tracker/product_list.html', {'products': products})

def deal_list(request):
    if not request.user.is_authenticated:
        return redirect('login')
    # Get all products for the user
    all_products = Product.objects.filter(user=request.user).order_by('-created_at')
    # Filter for deals in python since is_below_threshold is likely a property
    deals = [p for p in all_products if p.is_below_threshold]
    return render(request, 'tracker/deal_list.html', {'products': deals})

def search_tracked_products(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    query = request.GET.get('q', '')
    products = Product.objects.filter(user=request.user, name__icontains=query).order_by('-created_at')
    
    context = {
        'products': products,
        'search_query': query
    }
    return render(request, 'tracker/product_list.html', context)

def api_search_products(request):
    """API endpoint for live search."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
        
    products = Product.objects.filter(user=request.user, name__icontains=query).order_by('-created_at')[:5]
    
    results = []
    for p in products:
        results.append({
            'id': p.id,
            'name': p.name,
            'image_url': p.image_url,
            'current_price': float(p.current_price) if p.current_price else None,
            'currency': p.currency,
            'url': f"/product/{p.id}/" # Construct detail URL manually or use reverse in loop
        })
        
    return JsonResponse({'results': results})

def add_product(request):
    if request.method == 'POST':
        url = request.POST.get('url')
        target_price = request.POST.get('target_price')
        
        if url and target_price:
            try:
                target_price = float(target_price)
                details = get_product_details(url)
                
                if details['error']:
                    messages.error(request, f"Error scraping URL: {details['error']}")
                else:
                    product = Product.objects.create(
                        name=details['title'] or "Unknown Product",
                        url=url,
                        image_url=details.get('image_url'),
                        currency=details.get('currency', '₹'),
                        target_price=target_price,
                        current_price=details['price'],
                        last_checked=timezone.now() if details['price'] else None,
                        user=request.user
                    )
                    
                    if details['price']:
                        PriceHistory.objects.create(
                            product=product,
                            price=details['price']
                        )
                    
                    messages.success(request, "Product added successfully!")
            except ValueError:
                messages.error(request, "Invalid target price.")
        else:
            messages.error(request, "Please fill in all fields.")
            
    return redirect('dashboard')

from django.core.mail import send_mail
from django.conf import settings

def update_prices(request):
    products = Product.objects.filter(is_active=True)
    updated_count = 0
    
    for product in products:
        details = get_product_details(product.url)
        if not details['error'] and details['price']:
            old_price = product.current_price
            product.current_price = details['price']
            if details.get('image_url'):
                product.image_url = details['image_url']
            
            if details.get('currency'):
                product.currency = details['currency']
            
            # Only update title if it's valid and not in blacklist
            new_title = details.get('title')
            BLACKLIST_TITLES = ["Add to your order", "Amazon.in", "Shopping Cart", "Page Not Found", "Unknown Product"]
            
            if new_title and new_title not in BLACKLIST_TITLES:
                product.name = new_title
                
            product.last_checked = timezone.now()
            product.save()
            
            PriceHistory.objects.create(
                product=product,
                price=details['price']
            )
            updated_count += 1
            
            # Check for price drop and send email
            # Check for price drop and send email
            if product.is_below_threshold:
                print(f"DEBUG: Product {product.name} is below threshold!")
                print(f"DEBUG: Current: {product.current_price}, Target: {product.target_price}")
                
                subject = f"Price Drop Alert: {product.name}"
                message = f"Good news! The price for {product.name} has dropped to {product.current_price}. This is below your target of {product.target_price}.\n\nCheck it out here: {product.url}"
                from_email = settings.EMAIL_HOST_USER
                
                # Send to the product owner if they exist and have an email
                recipient_list = []
                if product.user and product.user.email:
                    recipient_list = [product.user.email]
                else:
                    # Fallback or skip? For now, let's log it.
                    print(f"DEBUG: No user linked to product {product.name}, skipping email.")
                
                if recipient_list:
                    print(f"DEBUG: Sending email to {recipient_list}")
                
                try:
                    send_mail(subject, message, from_email, recipient_list)
                    print(f"DEBUG: Email sent successfully for {product.name}")
                except Exception as e:
                    print(f"DEBUG: Failed to send email: {e}")
            else:
                print(f"DEBUG: Product {product.name} is NOT below threshold. Current: {product.current_price}, Target: {product.target_price}")


        elif details['error']:
            messages.warning(request, f"Failed to update {product.name}: {details['error']}")
            
    if updated_count > 0:
        messages.success(request, f"Updated {updated_count} products.")
    elif not messages.get_messages(request):
        messages.info(request, "No products updated.")
        
    return redirect('dashboard')

def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, "Product deleted.")
    return redirect('dashboard')

def get_price_history(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    history = product.price_history.all().order_by('timestamp')
    
    data = {
        'labels': [h.timestamp.strftime('%Y-%m-%d %H:%M:%S') for h in history],
        'prices': [float(h.price) for h in history],
        'currency': product.currency
    }
    
    from django.http import JsonResponse
    return JsonResponse(data)

from django.db.models import Min

def product_detail(request, product_id):
    """View product details and price history."""
    product = get_object_or_404(Product, id=product_id)
    
    # Auto-fetch price if it's None
    if product.current_price is None:
        details = get_product_details(product.url)
        if not details['error'] and details['price']:
            product.current_price = details['price']
            product.save()
            # Also create price history entry
            PriceHistory.objects.create(
                product=product,
                price=details['price']
            )
        else:
            # Fallback: Use search scraper if product page scraper fails
            # Search scrapers are more reliable than product page scrapers
            search_query = " ".join(product.name.split()[:5])
            search_results = search_products(search_query)
            
            # Use the first result's price if available
            if search_results and len(search_results) > 0:
                first_result = search_results[0]
                product.current_price = first_result['price']
                product.save()
                # Create price history entry
                PriceHistory.objects.create(
                    product=product,
                    price=first_result['price']
                )
    
    # Get price history for chart
    history = product.price_history.all().order_by('timestamp')
    
    # Calculate lowest price
    lowest_price = product.price_history.aggregate(Min('price'))['price__min']
    
    # Calculate deal score (0-100)
    deal_score = 0
    if product.current_price and product.target_price:
        ratio = float(product.target_price) / float(product.current_price)
        if ratio >= 1:
            deal_score = min(100, int(ratio * 100))
        else:
            deal_score = max(0, int((2 - (1/ratio)) * 100))
    
    # Calculate percentage difference if below target
    percentage_diff = None
    if product.current_price and product.target_price and product.current_price < product.target_price:
        diff = float(product.target_price) - float(product.current_price)
        percentage_diff = round((diff / float(product.target_price)) * 100, 1)
    
    context = {
        'product': product,
        'history': history,
        'deal_score': deal_score,
        'percentage_diff': percentage_diff,
        'lowest_price': lowest_price,
    }
    return render(request, 'tracker/product_detail.html', context)

def search_alternatives(request, product_id):
    """API endpoint to search for alternative prices."""
    try:
        product = Product.objects.get(id=product_id)
        # Use product name for search, stripping common noise words if needed
        query = product.name
        
        # Simple cleanup: take first 4-5 words to avoid over-specificity
        query = " ".join(query.split()[:5])
        
        # Search all marketplaces (including source)
        results = search_products(query)
        return JsonResponse({'results': results})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

from django.contrib.auth import login
from .forms import SignUpForm

def signup(request):
    try:
        if request.method == 'POST':
            form = SignUpForm(request.POST)
            if form.is_valid():
                user = form.save()
                login(request, user, backend='tracker.backends.EmailBackend')
                
                # Send welcome email
                # try:
                #     greeting_name = user.first_name if user.first_name else "there"
                #     send_mail(
                #         'Welcome to PriceTag!',
                #         f'Hi {greeting_name},\n\nThanks for signing up for PriceTag! You can now track product prices and get notified when they drop.\n\nHappy tracking!',
                #         settings.EMAIL_HOST_USER,
                #         [user.email],
                #         fail_silently=True,
                #     )
                # except Exception as e:
                #     print(f"Failed to send welcome email: {e}")
                    
                messages.success(request, "Registration successful!")
                return redirect('dashboard')
        else:
            form = SignUpForm()
        return render(request, 'tracker/signup.html', {'form': form})
    except Exception as e:
        import traceback
        print(f"Signup Error: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, f"Error: {str(e)}")
        return render(request, 'tracker/signup.html', {'form': SignUpForm(request.POST) if request.method == 'POST' else SignUpForm()})

from django.contrib.auth.decorators import login_required

@login_required
def profile(request):
    products = Product.objects.filter(user=request.user)
    total_products = products.count()
    
    # Calculate active deals (products below target price)
    active_deals = sum(1 for p in products if p.is_below_threshold)
    
    # Calculate potential savings
    potential_savings = sum(
        (p.target_price - p.current_price) 
        for p in products 
        if p.is_below_threshold and p.current_price and p.target_price
    )
    
    context = {
        'total_products': total_products,
        'active_deals': active_deals,
        'potential_savings': potential_savings,
    }
    context = {
        'total_products': total_products,
        'active_deals': active_deals,
        'potential_savings': potential_savings,
    }
    return render(request, 'tracker/profile.html', context)
