"""
Tour Package API Endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import Optional
from uuid import UUID
import csv
import io
from datetime import date, datetime

from ...schema.tour_package_schema import (
    TourPackageCreate,
    TourPackageUpdate,
    TourPackageListResponse,
    TourPackageDetailResponse,
    TourPackageCreateResponse,
    TourPackageUpdateResponse,
    TourPackageDeleteResponse,
    TourPackageBulkCreateResponse
)
from ...services.tour_package_service import TourPackageService
from ...core.supabase import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


def get_tour_package_service():
    """Dependency to get TourPackageService instance"""
    supabase = get_supabase_client()
    return TourPackageService(supabase)


@router.get("/", response_model=TourPackageListResponse)
async def get_tour_packages(
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    destination: Optional[str] = Query(None, description="Lọc theo điểm đến"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Số lượng kết quả"),
    offset: Optional[int] = Query(None, ge=0, description="Bỏ qua số lượng"),
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Lấy danh sách tất cả tour packages
    
    Args:
        is_active: Lọc theo trạng thái hoạt động (True/False)
        destination: Lọc theo điểm đến (tìm kiếm gần đúng)
        limit: Giới hạn số lượng kết quả trả về
        offset: Bỏ qua số lượng bản ghi
        service: Tour package service instance
        
    Returns:
        TourPackageListResponse với danh sách tour packages
        
    Example:
        GET /api/v1/tour-packages?is_active=true&limit=10
        GET /api/v1/tour-packages?destination=Đà Lạt
    """
    try:
        result = await service.get_all_packages(
            is_active=is_active,
            destination=destination,
            limit=limit,
            offset=offset
        )
        return TourPackageListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_tour_packages endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{package_id}", response_model=TourPackageDetailResponse)
async def get_tour_package(
    package_id: UUID,
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Lấy thông tin chi tiết một tour package
    
    Args:
        package_id: UUID của tour package
        service: Tour package service instance
        
    Returns:
        TourPackageDetailResponse với thông tin chi tiết tour package
        
    Example:
        GET /api/v1/tour-packages/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = await service.get_package_by_id(str(package_id))
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        
        return TourPackageDetailResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_tour_package endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=TourPackageCreateResponse, status_code=201)
async def create_tour_package(
    package: TourPackageCreate,
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Tạo mới một tour package
    
    Args:
        package: Dữ liệu tour package cần tạo
        service: Tour package service instance
        
    Returns:
        TourPackageCreateResponse với thông tin tour package đã tạo
        
    Example:
        POST /api/v1/tour-packages
        Body:
        {
            "package_name": "Tour Đà Lạt 3N2Đ",
            "destination": "Đà Lạt",
            "description": "Tour khám phá thành phố ngàn hoa",
            "duration_days": 3,
            "price": 2500000,
            "available_slots": 20,
            "start_date": "2024-12-01",
            "end_date": "2024-12-03",
            "image_urls": "https://example.com/img1.jpg|https://example.com/img2.jpg",
            "cuisine": "Ẩm thực miền Trung",
            "suitable_for": "Gia đình, Cặp đôi",
            "is_active": true
        }
    """
    try:
        # Convert to dict and handle date serialization
        package_data = package.model_dump()
        
        # Convert dates to ISO format strings
        if package_data.get('start_date'):
            package_data['start_date'] = package_data['start_date'].isoformat()
        if package_data.get('end_date'):
            package_data['end_date'] = package_data['end_date'].isoformat()
        
        result = await service.create_package(package_data)
        
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return TourPackageCreateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_tour_package endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{package_id}", response_model=TourPackageUpdateResponse)
async def update_tour_package(
    package_id: UUID,
    package: TourPackageUpdate,
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Cập nhật thông tin tour package
    
    Args:
        package_id: UUID của tour package cần cập nhật
        package: Dữ liệu cần cập nhật (các trường optional)
        service: Tour package service instance
        
    Returns:
        TourPackageUpdateResponse với thông tin tour package đã cập nhật
        
    Example:
        PUT /api/v1/tour-packages/123e4567-e89b-12d3-a456-426614174000
        Body:
        {
            "price": 2800000,
            "available_slots": 15,
            "is_active": true
        }
    """
    try:
        # Convert to dict and remove None values
        update_data = package.model_dump(exclude_unset=True)
        
        # Convert dates to ISO format strings if present
        if 'start_date' in update_data and update_data['start_date']:
            update_data['start_date'] = update_data['start_date'].isoformat()
        if 'end_date' in update_data and update_data['end_date']:
            update_data['end_date'] = update_data['end_date'].isoformat()
        
        result = await service.update_package(str(package_id), update_data)
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return TourPackageUpdateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_tour_package endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{package_id}", response_model=TourPackageDeleteResponse)
async def delete_tour_package(
    package_id: UUID,
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Xóa một tour package
    
    Args:
        package_id: UUID của tour package cần xóa
        service: Tour package service instance
        
    Returns:
        TourPackageDeleteResponse với kết quả xóa
        
    Example:
        DELETE /api/v1/tour-packages/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = await service.delete_package(str(package_id))
        
        if result["EC"] == 1:
            raise HTTPException(status_code=404, detail=result["EM"])
        elif result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        
        return TourPackageDeleteResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_tour_package endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/csv", response_model=TourPackageBulkCreateResponse, status_code=201)
async def create_tour_packages_from_csv(
    file: UploadFile = File(..., description="CSV file chứa dữ liệu tour packages"),
    service: TourPackageService = Depends(get_tour_package_service)
):
    """
    Tạo nhiều tour packages từ file CSV
    
    CSV file phải có các cột sau (header):
    - package_name: Tên gói tour (bắt buộc)
    - destination: Điểm đến (bắt buộc)
    - description: Mô tả chi tiết (bắt buộc)
    - duration_days: Số ngày tour (bắt buộc, số nguyên > 0)
    - price: Giá tour (bắt buộc, số thực > 0)
    - available_slots: Số chỗ còn trống (bắt buộc, số nguyên >= 0)
    - start_date: Ngày bắt đầu (bắt buộc, định dạng: YYYY-MM-DD)
    - end_date: Ngày kết thúc (bắt buộc, định dạng: YYYY-MM-DD)
    - image_urls: URL hình ảnh (tùy chọn, phân cách bằng |)
    - cuisine: Ẩm thực (tùy chọn)
    - suitable_for: Phù hợp cho (tùy chọn)
    - is_active: Trạng thái kích hoạt (tùy chọn, true/false, mặc định: true)
    
    Args:
        file: File CSV upload
        service: Tour package service instance
        
    Returns:
        TourPackageBulkCreateResponse với thống kê kết quả
        
    Example:
        POST /api/v1/tour-packages/bulk/csv
        Content-Type: multipart/form-data
        Body: CSV file
    """
    try:
        # Kiểm tra file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File phải có định dạng CSV")
        
        # Đọc nội dung file
        contents = await file.read()
        csv_text = contents.decode('utf-8-sig')  # utf-8-sig để xử lý BOM
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        # Kiểm tra header
        required_fields = [
            'package_name', 'destination', 'description', 'duration_days',
            'price', 'available_slots', 'start_date', 'end_date'
        ]
        
        if not csv_reader.fieldnames:
            raise HTTPException(status_code=400, detail="File CSV không có header")
        
        missing_fields = [field for field in required_fields if field not in csv_reader.fieldnames]
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Thiếu các cột bắt buộc: {', '.join(missing_fields)}"
            )
        
        # Parse và validate từng dòng
        packages_data = []
        errors = []
        row_num = 1  # Bắt đầu từ 1 (sau header)
        
        for row in csv_reader:
            row_num += 1
            try:
                # Parse và validate dữ liệu
                package_data = {
                    'package_name': row['package_name'].strip(),
                    'destination': row['destination'].strip(),
                    'description': row['description'].strip(),
                    'duration_days': int(row['duration_days']),
                    'price': float(row['price']),
                    'available_slots': int(row['available_slots']),
                    'start_date': datetime.strptime(row['start_date'].strip(), '%Y-%m-%d').date().isoformat(),
                    'end_date': datetime.strptime(row['end_date'].strip(), '%Y-%m-%d').date().isoformat(),
                }
                
                # Optional fields
                if row.get('image_urls'):
                    package_data['image_urls'] = row['image_urls'].strip()
                
                if row.get('cuisine'):
                    package_data['cuisine'] = row['cuisine'].strip()
                
                if row.get('suitable_for'):
                    package_data['suitable_for'] = row['suitable_for'].strip()
                
                # Parse is_active
                if row.get('is_active'):
                    is_active_str = row['is_active'].strip().lower()
                    package_data['is_active'] = is_active_str in ['true', '1', 'yes', 'y']
                else:
                    package_data['is_active'] = True
                
                # Validation
                if not package_data['package_name']:
                    raise ValueError("package_name không được để trống")
                if not package_data['destination']:
                    raise ValueError("destination không được để trống")
                if not package_data['description']:
                    raise ValueError("description không được để trống")
                if package_data['duration_days'] <= 0:
                    raise ValueError("duration_days phải lớn hơn 0")
                if package_data['price'] <= 0:
                    raise ValueError("price phải lớn hơn 0")
                if package_data['available_slots'] < 0:
                    raise ValueError("available_slots phải lớn hơn hoặc bằng 0")
                
                packages_data.append(package_data)
                
            except ValueError as e:
                errors.append(f"Dòng {row_num}: {str(e)}")
            except Exception as e:
                errors.append(f"Dòng {row_num}: Lỗi parse dữ liệu - {str(e)}")
        
        if not packages_data:
            raise HTTPException(
                status_code=400,
                detail=f"Không có dữ liệu hợp lệ để tạo. Lỗi: {'; '.join(errors)}"
            )
        
        # Tạo packages qua service
        result = await service.create_packages_bulk(packages_data)
        
        # Thêm parsing errors vào kết quả
        if errors:
            result['parsing_errors'] = errors
        
        return TourPackageBulkCreateResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_tour_packages_from_csv endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý file CSV: {str(e)}")
