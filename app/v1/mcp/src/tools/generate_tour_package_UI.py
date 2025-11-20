"""
MCP Tool - Generate Tour Package UI
Generate interactive UI components for tour packages using MCP-UI
"""
from fastmcp import FastMCP
from typing import List, Dict, Any
import logging
from mcp_ui_server import create_ui_resource
from mcp_ui_server.core import UIResource
from app.v1.mcp.src.schema import GenerateTourUIInput

logger = logging.getLogger(__name__)


def _generate_tour_card_html(package: Dict[str, Any]) -> str:
    """
    Generate HTML for a single tour card matching Angular component style
    
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
    image_urls_str = package.get("image_urls", "")
    description = package.get("description", "")
    start_date = package.get("start_date", "")
    available_slots = package.get("available_slots", 0)
    
    # Parse image URLs (pipe-separated)
    image_urls = [url.strip() for url in image_urls_str.split("|") if url.strip()]
    featured_image = image_urls[0] if image_urls else "https://via.placeholder.com/400x300"
    
    formatted_price = f"{int(price):,}".replace(",", ".")
    short_desc = description[:150] + "..." if len(description) > 150 else description
    
    # Build gallery button and modal
    gallery_html = ""
    if len(image_urls) > 1:
        gallery_images = "".join([f'<img src="{url}" alt="Tour" style="width: 100%; height: 150px; object-fit: cover; border-radius: 8px; cursor: pointer;" onclick="event.stopPropagation(); window.open(this.src, \'_blank\');">' for url in image_urls[:24]])
        gallery_button = f'<button onclick="this.nextElementSibling.style.display=\'block\'" style="width: 100%; margin-top: 12px; background: #667eea; color: white; border: none; padding: 8px; border-radius: 6px; font-size: 12px; cursor: pointer; font-weight: 600;">Xem tất cả {len(image_urls)} ảnh</button>'
        gallery_modal = f'<div style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 1000; padding: 20px; overflow-y: auto;" onclick="this.style.display=\'none\'"><div style="max-width: 900px; margin: 0 auto;"><div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px;">{gallery_images}</div></div></div>'
        gallery_html = gallery_button + gallery_modal
    
    html = f"""
    <div style="
        width: 100%;
        max-width: 350px;
        background: white;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s, box-shadow 0.2s;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        cursor: pointer;
        margin: 10px;
    " onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 4px 16px rgba(0,0,0,0.15)'" 
       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(0,0,0,0.1)'">
        
        <!-- Image -->
        <div style="position: relative; width: 100%; height: 200px; overflow: hidden;">
            <img src="{featured_image}" 
                 alt="{package_name}"
                 style="width: 100%; height: 100%; object-fit: cover;"
                 onerror="this.src='https://via.placeholder.com/400x300?text=No+Image'">
            
            <!-- Duration Badge -->
            <div style="
                position: absolute;
                top: 12px;
                right: 12px;
                background: rgba(255, 255, 255, 0.95);
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                color: #333;
                backdrop-filter: blur(4px);
            ">
                🕒 {duration_days} ngày
            </div>
        </div>
        
        <!-- Content -->
        <div style="padding: 16px;">
            <!-- Title -->
            <h3 style="
                margin: 0 0 8px 0;
                font-size: 18px;
                font-weight: 700;
                color: #1a1a1a;
                line-height: 1.3;
            ">{package_name}</h3>
            
            <!-- Destination -->
            <div style="
                display: flex;
                align-items: center;
                gap: 6px;
                margin-bottom: 12px;
                color: #666;
                font-size: 14px;
            ">
                <span style="font-size: 16px;">📍</span>
                <span>{destination}</span>
            </div>
            
            <!-- Description -->
            <p style="
                margin: 0 0 16px 0;
                font-size: 13px;
                color: #666;
                line-height: 1.5;
                min-height: 60px;
            ">{short_desc}</p>
            
            <!-- Footer -->
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding-top: 16px;
                border-top: 1px solid #eee;
            ">
                <!-- Price -->
                <div>
                    <div style="
                        font-size: 20px;
                        font-weight: 700;
                        color: #e53e3e;
                    ">{formatted_price} ₫</div>
                    <div style="
                        font-size: 11px;
                        color: #999;
                        margin-top: 2px;
                    ">/ người</div>
                </div>
                
                <!-- Book Button -->
                <button onclick="handleBooking('{package_id}', '{package_name}')" style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: opacity 0.2s;
                " onmouseover="this.style.opacity='0.9'" 
                   onmouseout="this.style.opacity='1'">
                    Đặt ngay
                </button>
            </div>
            
            <!-- Additional Info -->
            <div style="
                margin-top: 12px;
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                color: #999;
            ">
                <span>🗓️ {start_date}</span>
                <span>👥 Còn {available_slots} chỗ</span>
            </div>
            {gallery_html}
        </div>
    </div>
    """
    
    return html


def _generate_tour_grid_html(packages: List[Dict[str, Any]]) -> str:
    """
    Generate complete HTML page with tour cards grid
    
    Args:
        packages: List of tour package dicts
        
    Returns:
        Complete HTML document
    """
    cards_html = "\n".join([_generate_tour_card_html(pkg) for pkg in packages])
    
    html = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tour Packages</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            .header {{
                text-align: center;
                color: white;
                margin-bottom: 30px;
            }}
            
            .header h1 {{
                font-size: 32px;
                font-weight: 700;
                margin-bottom: 10px;
            }}
            
            .header p {{
                font-size: 16px;
                opacity: 0.9;
            }}
            
            .tour-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                gap: 20px;
                justify-items: center;
            }}
            
            @media (max-width: 768px) {{
                .tour-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌴 Gói Tour Du Lịch Đặc Biệt</h1>
                <p>Khám phá những điểm đến tuyệt vời với giá ưu đãi</p>
            </div>
            
            <div class="tour-grid">
                {cards_html}
            </div>
        </div>
        
        <script>
            function handleBooking(packageId, packageName) {{
                // Send tool call to parent (MCP host)
                if (window.parent) {{
                    window.parent.postMessage({{
                        type: 'tool',
                        payload: {{
                            toolName: 'create_booking',
                            params: {{
                                package_id: packageId,
                                package_name: packageName,
                                source: 'ui_component'
                            }}
                        }}
                    }}, '*');
                }}
                
                // Also show alert for user feedback
                alert(`Đang xử lý booking cho tour: ${{packageName}}\\nID: ${{packageId}}`);
            }}
        </script>
    </body>
    </html>
    """
    
    return html


from pydantic import ValidationError

def register_tour_ui_tools(mcp: FastMCP):
    """
    Register tour package UI generation tools
    
    Args:
        mcp: FastMCP instance
    """
    
    @mcp.tool()
    def generate_tour_ui(packages: List[Dict[str, Any]]) -> List[UIResource]:
        """
        Generate interactive UI for tour packages using MCP-UI standard.
        
        Creates responsive HTML grid of tour cards with images, pricing, and gallery modals.
        
        Returns:
            List containing UIResource with the tour grid HTML
        """
        try:
            # Validate inputs
            validated = GenerateTourUIInput(packages=packages)
            
            if not validated.packages:
                logger.warning("No packages provided to generate_tour_ui")
                return []
            
            logger.info(f"Generating UI for {len(packages)} tour packages")
            
            # Generate HTML
            html_content = _generate_tour_grid_html(packages)
            
            # Create UI Resource following MCP-UI standard
            ui_resource = create_ui_resource({
                "uri": f"ui://tour-packages/grid-{len(packages)}",
                "content": {
                    "type": "rawHtml",
                    "htmlString": html_content
                },
                "encoding": "text"
            })
            
            logger.info(f"Successfully created UIResource with URI: {ui_resource.resource.uri}")
            return [ui_resource]
            
        except ValidationError as e:
            logger.error(f"Validation Error in generate_tour_ui: {e}")
            # Return error UI for validation
            error_html = f"""
            <div style="padding: 20px; text-align: center; font-family: Arial, sans-serif;">
                <h2 style="color: #e53e3e;">⚠️ Lỗi dữ liệu đầu vào</h2>
                <p style="color: #666;">Dữ liệu tour không hợp lệ.</p>
                <p style="color: #999; font-size: 12px;">Error: {str(e)}</p>
            </div>
            """
            error_resource = create_ui_resource({
                "uri": "ui://tour-packages/validation-error",
                "content": {"type": "rawHtml", "htmlString": error_html},
                "encoding": "text"
            })
            return [error_resource]
            
        except Exception as e:
            logger.error(f"Failed to generate tour UI: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Return error UI
            error_html = f"""
            <div style="padding: 20px; text-align: center; font-family: Arial, sans-serif;">
                <h2 style="color: #e53e3e;">⚠️ Lỗi tạo giao diện</h2>
                <p style="color: #666;">Không thể hiển thị tour packages.</p>
                <p style="color: #999; font-size: 12px;">Error: {str(e)}</p>
            </div>
            """
            
            error_resource = create_ui_resource({
                "uri": "ui://tour-packages/error",
                "content": {
                    "type": "rawHtml",
                    "htmlString": error_html
                },
                "encoding": "text"
            })
            
            return [error_resource]
