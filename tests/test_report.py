"""
Test Report Service
"""
import pytest
from datetime import date


def test_price_range_logic_explanation():
    """
    Test để minh họa logic phân loại giá và tính tổng số người
    
    Ví dụ dữ liệu:
    - Tour A (giá 3M) - budget: 
        - Booking 1: 5 người
        - Booking 2: 3 người
    - Tour B (giá 4M) - budget:
        - Booking 3: 2 người
    - Tour C (giá 10M) - medium:
        - Booking 4: 4 người
    - Tour D (giá 20M) - premium:
        - Booking 5: 6 người
        
    Kết quả mong đợi:
    - budget: 5 + 3 + 2 = 10 người (2 tours)
    - medium: 4 người (1 tour)
    - premium: 6 người (1 tour)
    """
    
    # Giả lập dữ liệu bookings đã join với tour_packages
    bookings = [
        # Tour A - giá 3M (budget)
        {"booking_id": "1", "package_id": "A", "number_of_people": 5, 
         "tour_packages": {"package_id": "A", "price": 3_000_000}},
        {"booking_id": "2", "package_id": "A", "number_of_people": 3,
         "tour_packages": {"package_id": "A", "price": 3_000_000}},
        
        # Tour B - giá 4M (budget)
        {"booking_id": "3", "package_id": "B", "number_of_people": 2,
         "tour_packages": {"package_id": "B", "price": 4_000_000}},
        
        # Tour C - giá 10M (medium)
        {"booking_id": "4", "package_id": "C", "number_of_people": 4,
         "tour_packages": {"package_id": "C", "price": 10_000_000}},
        
        # Tour D - giá 20M (premium)
        {"booking_id": "5", "package_id": "D", "number_of_people": 6,
         "tour_packages": {"package_id": "D", "price": 20_000_000}},
    ]
    
    # Logic phân loại giá
    def get_price_range_category(price: float) -> str:
        if price < 5_000_000:
            return "budget"
        elif price < 15_000_000:
            return "medium"
        else:
            return "premium"
    
    # Tính toán
    stats = {
        "budget": {"total_people": 0, "tour_ids": set()},
        "medium": {"total_people": 0, "tour_ids": set()},
        "premium": {"total_people": 0, "tour_ids": set()}
    }
    
    for booking in bookings:
        package = booking["tour_packages"]
        price = float(package["price"])
        package_id = booking["package_id"]
        
        # Xác định phân khúc giá dựa vào price của tour
        price_range = get_price_range_category(price)
        
        # Cộng số người vào phân khúc tương ứng
        stats[price_range]["total_people"] += booking["number_of_people"]
        stats[price_range]["tour_ids"].add(package_id)
    
    # Kiểm tra kết quả
    assert stats["budget"]["total_people"] == 10, "Budget: 5 + 3 + 2 = 10"
    assert len(stats["budget"]["tour_ids"]) == 2, "Budget có 2 tours (A, B)"
    
    assert stats["medium"]["total_people"] == 4, "Medium: 4"
    assert len(stats["medium"]["tour_ids"]) == 1, "Medium có 1 tour (C)"
    
    assert stats["premium"]["total_people"] == 6, "Premium: 6"
    assert len(stats["premium"]["tour_ids"]) == 1, "Premium có 1 tour (D)"
    
    print("✅ Logic đúng:")
    print(f"Budget (<5M): {stats['budget']['total_people']} người từ {len(stats['budget']['tour_ids'])} tours")
    print(f"Medium (5M-15M): {stats['medium']['total_people']} người từ {len(stats['medium']['tour_ids'])} tours")
    print(f"Premium (>15M): {stats['premium']['total_people']} người từ {len(stats['premium']['tour_ids'])} tours")


if __name__ == "__main__":
    test_price_range_logic_explanation()
