"""
UI Generator - Generate HTML for tour packages
Direct HTML generation without MCP tool calls
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def _build_highlights_section(highlights: list, itinerary_snippet: str, escape_html_func) -> str:
    """Build highlights or itinerary snippet section HTML - Simple and clean"""
    highlights_html = ""
    if highlights:
        highlights_html = '<div style="display: flex; flex-wrap: wrap; gap: 6px;">'
        for h in highlights[:4]:
            highlights_html += f'<span style="font-size: 12px; padding: 4px 10px; background: #f1f5f9; border-radius: 6px; color: #475569; font-weight: 500;">{escape_html_func(str(h))}</span>'
        highlights_html += '</div>'
    
    snippet_html = ""
    if itinerary_snippet and not highlights:
        snippet_text = itinerary_snippet[:100] + "..." if len(itinerary_snippet) > 100 else itinerary_snippet
        snippet_html = f'<p style="margin: 0; font-size: 13px; color: #64748b; line-height: 1.5;">{escape_html_func(snippet_text)}</p>'
    
    if highlights_html or snippet_html:
        return f'''
            <div style="margin: 0; padding: 0;">
                {highlights_html}
                {snippet_html}
            </div>
        '''
    return ""


def generate_tour_card_html(package: Dict[str, Any]) -> str:
    """
    Generate HTML for a single tour card
    
    Args:
        package: Tour package data dict
        
    Returns:
        HTML string for tour card
    """
    package_id = package.get("package_id", "")
    package_name = package.get("package_name", "Unknown Tour")
    destination = package.get("destination", "Unknown")
    duration_days = package.get("duration_days", 0)
    price = package.get("price", 0)
    
    # Handle both image_url (singular) and image_urls (plural) fields
    # Check multiple possible field names
    image_urls_str = (
        package.get("image_urls", "") 
    )
    
    description = package.get("description", "")
    start_date = package.get("start_date", "")
    available_slots = package.get("available_slots", 0)
    
    # Log for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📦 Card for: {package_name} | Image URL: {image_urls_str[:80] if image_urls_str else 'None'} | Price: {price}")
    
    # Parse image URLs (pipe-separated or single URL)
    image_urls = []
    if image_urls_str:
        # Check if it's pipe-separated or single URL
        if "|" in str(image_urls_str):
            image_urls = [url.strip() for url in str(image_urls_str).split("|") if url.strip()]
        else:
            image_urls = [str(image_urls_str).strip()] if str(image_urls_str).strip() else []
    
    # REVERSE image list as requested by user (take from end)
    if image_urls:
        image_urls.reverse()
    
    # Use actual tour image if available, otherwise placeholder
    featured_image = image_urls[0] if image_urls else "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=400&h=300&fit=crop"
    
    # Format price
    formatted_price = f"{int(price):,}".replace(",", ".")
    
    # Get additional info if available
    highlights = package.get("highlights", [])
    itinerary_snippet = package.get("itinerary_snippet", "")
    end_date = package.get("end_date", "")
    suitable_for = package.get("suitable_for", "")
    cuisine = package.get("cuisine", "")
    
    # Build gallery - show first 3 images in a nice row
    gallery_html = ""
    if len(image_urls) > 1:
        gallery_images = image_urls[1:4]  # Skip featured image
        gallery_items = []
        for url in gallery_images:
            gallery_items.append(f'''
                <div style="
                    flex: 1; 
                    aspect-ratio: 4/3; 
                    border-radius: 8px; 
                    overflow: hidden; 
                    cursor: pointer;
                    background: #f1f5f9;
                " onclick="window.open('{url}', '_blank')">
                    <img src="{url}" style="width: 100%; height: 100%; object-fit: cover; display: block;" loading="lazy">
                </div>
            ''')
        
        if gallery_items:
            gallery_html = f"""
                <div style="display: flex; gap: 8px; margin-top: 12px;">
                    {''.join(gallery_items)}
                </div>
            """

    # Escape HTML special characters in text content
    def escape_html(text: str) -> str:
        return (str(text)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;"))
    
    html = f"""
    <div class="tour-card-clean" style="
        width: calc(100% - 200px);
        max-width: 900px;
        background: #ffffff;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
        display: flex;
        flex-direction: column;
        margin-bottom: 20px;
        cursor: pointer;
    " onclick="handleBooking('{package_id}', {repr(package_name)})">
        
        <!-- Featured Image (Top) -->
        <div style="position: relative; width: 100%; aspect-ratio: 16/9; overflow: hidden; background: #f8fafc;">
            <img src="{featured_image}" 
                 alt="Tour image"
                 style="width: 100%; height: 100%; object-fit: cover; display: block;"
                 loading="lazy">
            
            <div style="
                position: absolute;
                top: 12px;
                right: 12px;
                background: rgba(255, 255, 255, 0.95);
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                color: #0f172a;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                {duration_days} ngày
            </div>
        </div>
        
        <!-- Card Body -->
        <div style="padding: 16px; display: flex; flex-direction: column; gap: 12px;">
            
            <!-- Title & Location -->
            <div>
                <h3 style="
                    margin: 0 0 6px 0;
                    font-size: 18px;
                    font-weight: 700;
                    color: #1e293b;
                    line-height: 1.4;
                ">{escape_html(package_name)}</h3>
                
                <div style="display: flex; align-items: center; gap: 6px; font-size: 13px; color: #64748b;">
                    <span>📍</span>
                    <span>{escape_html(destination)}</span>
                </div>
            </div>

            <!-- Additional Info: Dates, Suitable For, Cuisine -->
            <div style="display: flex; flex-wrap: wrap; gap: 8px; font-size: 12px; color: #64748b;">
                {f'<div style="display: flex; align-items: center; gap: 4px;"><span>📅</span><span>{escape_html(str(start_date))}</span>{f" → {escape_html(str(end_date))}" if end_date else ""}</div>' if start_date else ''}
                {f'<div style="display: flex; align-items: center; gap: 4px;"><span>👥</span><span>{escape_html(str(suitable_for))}</span></div>' if suitable_for else ''}
                {f'<div style="display: flex; align-items: center; gap: 4px;"><span>🍽️</span><span>{escape_html(str(cuisine))}</span></div>' if cuisine else ''}
            </div>

            <!-- Highlights/Snippet -->
            {_build_highlights_section(highlights, itinerary_snippet, escape_html) if (highlights or itinerary_snippet) else ''}
            
            <!-- Mini Gallery (Row of 3) -->
            {gallery_html}
            
            <!-- Footer (Price & Slots) -->
            <div style="
                margin-top: 8px;
                padding-top: 16px;
                border-top: 1px solid #f1f5f9;
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
            ">
                <div>
                    <div style="font-size: 12px; color: #64748b; margin-bottom: 2px;">Giá từ</div>
                    <div style="font-size: 20px; font-weight: 700; color: #ef4444;">{formatted_price} ₫</div>
                </div>
                
                <div style="text-align: right; font-size: 13px; color: #64748b;">
                    <div style="color: #22c55e; font-weight: 500;">Còn {available_slots} chỗ</div>
                </div>
            </div>
        </div>
    </div>
    """
    
    return html


def generate_tour_grid_html(packages: List[Dict[str, Any]]) -> str:
    """
    Generate complete HTML page with tour cards grid
    
    Args:
        packages: List of tour package dicts
        
    Returns:
        HTML string (just the grid part, not full document)
    """
    cards_html = "\n".join([generate_tour_card_html(pkg) for pkg in packages])
    
    html = f"""
    <div class="mcp-tour-grid-wrapper" style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        padding: 0;
        width: 100%;
        max-width: 100%;
        background: transparent;
        margin: 0;
    ">
        <div class="mcp-tour-grid" style="
            display: flex;
            flex-direction: column;
            gap: 24px;
            width: 100%;
            max-width: 100%;
            padding: 0;
            margin: 0;
        ">
            {cards_html}
        </div>
    </div>
    
    <script>
        function handleBooking(packageId, packageName) {{
            // Send message to Angular component
            if (window.parent && window.parent.postMessage) {{
                window.parent.postMessage({{
                    type: 'mcp_ui_booking',
                    packageId: packageId,
                    packageName: packageName
                }}, '*');
            }}
            
            // Also trigger Angular event if available
            if (window.dispatchEvent) {{
                window.dispatchEvent(new CustomEvent('mcpBooking', {{
                    detail: {{ packageId, packageName }}
                }}));
            }}
            
            console.log('Booking requested:', packageId, packageName);
        }}
    </script>
    """
    
    return html


def generate_payment_button_html(
    payment_url: str,
    booking_id: str,
    total_amount: float,
    tour_name: str,
    payment_method: str = "vnpay"
) -> str:
    """
    Generate HTML for payment button component
    
    Args:
        payment_url: VNPay payment URL
        booking_id: Booking ID
        total_amount: Total amount to pay
        tour_name: Tour package name
        payment_method: Payment method (vnpay)
        
    Returns:
        HTML string for payment button component
    """
    # Format price
    formatted_price = f"{int(total_amount):,}".replace(",", ".")
    
    # Escape HTML để tránh XSS
    def escape_html(text: str) -> str:
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")
    
    safe_tour_name = escape_html(tour_name)
    safe_payment_url = escape_html(payment_url)
    safe_booking_id = escape_html(booking_id)
    
    html = f"""
    <div class="mcp-payment-button-wrapper" style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        padding: 0;
        width: 100%;
        max-width: 100%;
        background: transparent;
        margin: 16px 0;
    ">
        <div class="mcp-payment-card" style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            color: white;
        ">
            <div style="margin-bottom: 16px;">
                <h3 style="
                    margin: 0 0 8px 0;
                    font-size: 18px;
                    font-weight: 600;
                    color: white;
                ">💳 Thanh toán đặt tour</h3>
                <p style="
                    margin: 0;
                    font-size: 14px;
                    color: rgba(255, 255, 255, 0.9);
                    opacity: 0.95;
                ">{safe_tour_name}</p>
            </div>
            
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding: 12px;
                background: rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                backdrop-filter: blur(10px);
            ">
                <span style="font-size: 14px; color: rgba(255, 255, 255, 0.9);">Tổng tiền:</span>
                <span style="font-size: 20px; font-weight: 700; color: white;">{formatted_price} VNĐ</span>
            </div>
            
            <button 
                class="mcp-payment-button"
                data-payment-url="{safe_payment_url}"
                data-booking-id="{safe_booking_id}"
                style="
                    width: 100%;
                    padding: 14px 24px;
                    background: white;
                    color: #667eea;
                    border: none;
                    border-radius: 10px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                "
                onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 8px rgba(0, 0, 0, 0.15)';"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0, 0, 0, 0.1)';"
            >
                <span>💳</span>
                <span>Thanh toán ngay qua VNPay</span>
            </button>
            
            <p style="
                margin: 12px 0 0 0;
                font-size: 12px;
                color: rgba(255, 255, 255, 0.8);
                text-align: center;
            ">Bạn sẽ được chuyển đến trang thanh toán VNPay</p>
        </div>
    </div>
    
    """
    
    return html

