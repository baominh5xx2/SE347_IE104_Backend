"""
FalkorDB Client - Quản lý kết nối và truy vấn FalkorDB
"""
from falkordb import FalkorDB
from typing import Optional, Dict, Any
from src.mcp_server.core.config import settings
import logging

logger = logging.getLogger(__name__)


class FalkorDBClient:
    """FalkorDB client singleton"""
    
    _instance: Optional['FalkorDBClient'] = None
    _db: Optional[FalkorDB] = None
    _graph = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def connect(self):
        """Kết nối đến FalkorDB"""
        if self._db is None:
            try:
                # Chuẩn bị connection parameters
                connection_params = {
                    'host': settings.FALKORDB_HOST,
                    'port': settings.FALKORDB_PORT,
                }
                
                # Thêm username/password nếu có
                if hasattr(settings, 'FALKORDB_USERNAME') and settings.FALKORDB_USERNAME:
                    connection_params['username'] = settings.FALKORDB_USERNAME
                
                if hasattr(settings, 'FALKORDB_PASSWORD') and settings.FALKORDB_PASSWORD:
                    connection_params['password'] = settings.FALKORDB_PASSWORD
                
                # Thêm SSL nếu có
                if hasattr(settings, 'FALKORDB_SSL'):
                    connection_params['ssl'] = settings.FALKORDB_SSL
                
                self._db = FalkorDB(**connection_params)
                self._graph = self._db.select_graph(settings.FALKORDB_DATABASE)
                logger.info(f"✅ Connected to FalkorDB: {settings.FALKORDB_HOST}:{settings.FALKORDB_PORT}")
                logger.info(f"📊 Using graph database: {settings.FALKORDB_DATABASE}")
                if connection_params.get('username'):
                    logger.info(f"🔐 Authenticated as: {connection_params['username']}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to FalkorDB: {str(e)}")
                raise
        return self._graph
    
    def get_graph(self):
        """Lấy graph instance"""
        if self._graph is None:
            return self.connect()
        return self._graph
    
    def close(self):
        """Đóng kết nối"""
        if self._db is not None:
            self._db = None
            self._graph = None
            logger.info("Closed FalkorDB connection")


def get_falkordb_graph():
    """Helper function để lấy graph instance"""
    client = FalkorDBClient()
    return client.get_graph()


def create_booking_in_falkordb(
    booking_id: str,
    user_name: str,
    user_phone: str,
    user_email: str,
    package_id: str,
    package_name: str,
    destination: str,
    number_of_people: int,
    total_amount: float,
    travel_date: str,
    package_price: float,
    duration_days: int,
    departure_location: str,
    status: str = "pending",
    special_requests: Optional[str] = None,
    contact_name: Optional[str] = None,
    contact_phone: Optional[str] = None
) -> Dict[str, Any]:
    """
    Lưu booking vào FalkorDB dưới dạng graph với thông tin đầy đủ
    
    Structure (matched with migrate_bookings_to_falkordb.py):
    (User)-[:MADE_BOOKING]->(Booking)-[:FOR_PACKAGE]->(TourPackage)
    (User)-[:BOOKED]->(TourPackage)
    
    Args:
        booking_id: ID của booking
        user_name: Tên user
        user_phone: Số điện thoại user
        user_email: Email user
        package_id: ID tour package
        package_name: Tên tour package
        destination: Địa điểm đến
        number_of_people: Số người
        total_amount: Tổng tiền
        travel_date: Ngày đi
        package_price: Giá tour/người
        duration_days: Số ngày tour
        departure_location: Điểm khởi hành
        status: Trạng thái booking (pending/confirmed/cancelled/completed)
        special_requests: Yêu cầu đặc biệt
        contact_name: Tên người liên hệ
        contact_phone: SĐT người liên hệ
        
    Returns:
        Kết quả lưu vào FalkorDB
    """
    try:
        from datetime import datetime
        
        graph = get_falkordb_graph()
        
        # Use parameterized queries to avoid SQL injection and escaping issues
        current_timestamp = datetime.now().isoformat()
        
        # Cypher query matching migrate_bookings_to_falkordb.py structure
        query = """
        // Create or merge User node
        MERGE (u:User {phone: $phone})
        ON CREATE SET 
            u.name = $name,
            u.email = $email,
            u.created_at = $timestamp
        ON MATCH SET
            u.name = $name,
            u.email = $email
        
        // Create or merge TourPackage node
        MERGE (p:TourPackage {package_id: $package_id})
        ON CREATE SET
            p.name = $package_name,
            p.destination = $destination,
            p.price = $price,
            p.duration_days = $duration_days,
            p.departure_location = $departure_location
        ON MATCH SET
            p.name = $package_name,
            p.destination = $destination,
            p.price = $price,
            p.duration_days = $duration_days,
            p.departure_location = $departure_location
        
        // Create Booking node
        CREATE (b:Booking {
            booking_id: $booking_id,
            number_of_people: $number_of_people,
            total_amount: $total_amount,
            status: $status,
            special_requests: $special_requests,
            created_at: $created_at,
            travel_date: $travel_date,
            package_price: $price,
            contact_name: $contact_name,
            contact_phone: $contact_phone
        })
        
        // Create relationships
        CREATE (u)-[:MADE_BOOKING]->(b)
        CREATE (b)-[:FOR_PACKAGE]->(p)
        CREATE (u)-[:BOOKED {
            booking_date: $created_at,
            total_amount: $total_amount,
            status: $status
        }]->(p)
        
        RETURN b.booking_id as booking_id, u.phone as user_phone, p.name as package_name
        """
        
        params = {
            'phone': user_phone,
            'name': user_name,
            'email': user_email or '',
            'booking_id': booking_id,
            'package_id': package_id,
            'package_name': package_name,
            'destination': destination,
            'price': package_price,
            'duration_days': duration_days,
            'departure_location': departure_location,
            'number_of_people': number_of_people,
            'total_amount': total_amount,
            'status': status,
            'special_requests': special_requests or '',
            'created_at': current_timestamp,
            'travel_date': travel_date or '',
            'contact_name': contact_name or user_name,
            'contact_phone': contact_phone or user_phone,
            'timestamp': current_timestamp
        }
        
        result = graph.query(query, params)
        
        logger.info(f"✅ Saved booking {booking_id} to FalkorDB with full details")
        logger.info(f"   User: {user_name} ({user_phone})")
        logger.info(f"   Package: {package_name}")
        logger.info(f"   Destination: {destination}")
        logger.info(f"   Travel date: {travel_date or 'Not specified'}")
        logger.info(f"   Total amount: {total_amount:,.0f} VNĐ")
        
        return {
            "success": True,
            "booking_id": booking_id,
            "message": "Booking đã được lưu vào FalkorDB graph database với đầy đủ thông tin"
        }
        
    except Exception as e:
        logger.error(f"❌ Error saving to FalkorDB: {str(e)}")
        return {
            "success": False,
            "error": f"Lỗi khi lưu vào FalkorDB: {str(e)}"
        }


def get_user_bookings_from_falkordb(user_phone: str) -> Dict[str, Any]:
    """
    Lấy tất cả bookings của user từ FalkorDB với đầy đủ thông tin
    
    Args:
        user_phone: Số điện thoại user
        
    Returns:
        Danh sách bookings với đầy đủ chi tiết
    """
    try:
        graph = get_falkordb_graph()
        
        query = f"""
        MATCH (u:User {{phone: '{user_phone}'}})-[:MADE_BOOKING]->(b:Booking)-[:FOR_PACKAGE]->(p:TourPackage)
        RETURN b.booking_id as booking_id,
               b.number_of_people as number_of_people,
               b.total_amount as total_amount,
               b.travel_date as travel_date,
               b.status as status,
               b.special_requests as special_requests,
               b.contact_name as contact_name,
               b.contact_phone as contact_phone,
               b.created_at as created_at,
               b.package_price as package_price,
               u.name as user_name,
               p.package_id as package_id,
               p.name as package_name,
               p.price as price,
               p.duration_days as duration_days,
               p.destination as destination,
               p.departure_location as departure_location
        ORDER BY b.created_at DESC
        """
        
        result = graph.query(query)
        
        bookings = []
        for row in result.result_set:
            bookings.append({
                "booking_id": row[0],
                "number_of_people": row[1],
                "total_amount": row[2],
                "travel_date": row[3],
                "status": row[4],
                "special_requests": row[5],
                "contact_name": row[6],
                "contact_phone": row[7],
                "created_at": row[8],
                "package_price": row[9],
                "user_name": row[10],
                "package_id": row[11],
                "package_name": row[12],
                "price": row[13],
                "duration_days": row[14],
                "destination": row[15],
                "departure_location": row[16]
            })
        
        logger.info(f"✅ Retrieved {len(bookings)} bookings for user {user_phone} from FalkorDB")
        
        return {
            "success": True,
            "user_phone": user_phone,
            "bookings": bookings,
            "total_bookings": len(bookings)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting bookings from FalkorDB: {str(e)}")
        return {
            "success": False,
            "error": f"Lỗi khi lấy bookings từ FalkorDB: {str(e)}"
        }


def get_all_users_from_falkordb() -> Dict[str, Any]:
    """
    Lấy tất cả users từ FalkorDB
    
    Returns:
        Danh sách tất cả users
    """
    try:
        graph = get_falkordb_graph()
        
        query = """
        MATCH (u:User)
        RETURN u.phone as phone, u.name as name, u.email as email
        ORDER BY u.name
        """
        
        result = graph.query(query)
        
        users = []
        for row in result.result_set:
            users.append({
                "phone": row[0],
                "name": row[1],
                "email": row[2]
            })
        
        logger.info(f"✅ Retrieved {len(users)} users from FalkorDB")
        
        return {
            "success": True,
            "users": users,
            "total": len(users)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting users from FalkorDB: {str(e)}")
        return {
            "success": False,
            "error": f"Lỗi khi lấy users từ FalkorDB: {str(e)}"
        }


def get_all_tour_packages_from_falkordb() -> Dict[str, Any]:
    """
    Lấy tất cả tour packages từ FalkorDB với thông tin destination và location
    
    Returns:
        Danh sách tất cả tour packages
    """
    try:
        graph = get_falkordb_graph()
        
        query = """
        MATCH (p:TourPackage)
        RETURN p.package_id as package_id,
               p.name as name,
               p.price as price,
               p.duration_days as duration_days,
               p.destination as destination,
               p.departure_location as departure_location
        ORDER BY p.destination, p.name
        """
        
        result = graph.query(query)
        
        packages = []
        for row in result.result_set:
            packages.append({
                "package_id": row[0],
                "name": row[1],
                "price": row[2],
                "duration_days": row[3],
                "destination": row[4],
                "departure_location": row[5]
            })
        
        logger.info(f"✅ Retrieved {len(packages)} tour packages from FalkorDB")
        
        return {
            "success": True,
            "packages": packages,
            "total": len(packages)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting tour packages from FalkorDB: {str(e)}")
        return {
            "success": False,
            "error": f"Lỗi khi lấy tour packages từ FalkorDB: {str(e)}"
        }


def get_all_bookings_from_falkordb() -> Dict[str, Any]:
    """
    Lấy tất cả bookings từ FalkorDB với đầy đủ thông tin liên quan
    
    Returns:
        Danh sách tất cả bookings
    """
    try:
        graph = get_falkordb_graph()
        
        query = """
        MATCH (u:User)-[:MADE_BOOKING]->(b:Booking)-[:FOR_PACKAGE]->(p:TourPackage)
        RETURN b.booking_id as booking_id,
               b.number_of_people as number_of_people,
               b.total_amount as total_amount,
               b.travel_date as travel_date,
               b.status as status,
               b.created_at as created_at,
               b.contact_name as contact_name,
               b.contact_phone as contact_phone,
               u.name as user_name,
               u.phone as user_phone,
               p.package_id as package_id,
               p.name as package_name,
               p.destination as destination,
               p.departure_location as departure_location
        ORDER BY b.created_at DESC
        """
        
        result = graph.query(query)
        
        bookings = []
        for row in result.result_set:
            bookings.append({
                "booking_id": row[0],
                "number_of_people": row[1],
                "total_amount": row[2],
                "travel_date": row[3],
                "status": row[4],
                "created_at": row[5],
                "contact_name": row[6],
                "contact_phone": row[7],
                "user_name": row[8],
                "user_phone": row[9],
                "package_id": row[10],
                "package_name": row[11],
                "destination": row[12],
                "departure_location": row[13]
            })
        
        logger.info(f"✅ Retrieved {len(bookings)} bookings from FalkorDB")
        
        return {
            "success": True,
            "bookings": bookings,
            "total": len(bookings)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting bookings from FalkorDB: {str(e)}")
        return {
            "success": False,
            "error": f"Lỗi khi lấy bookings từ FalkorDB: {str(e)}"
        }


def get_booking_details_from_falkordb(booking_id: str) -> Dict[str, Any]:
    """
    Lấy chi tiết đầy đủ của một booking từ FalkorDB
    
    Args:
        booking_id: ID của booking
        
    Returns:
        Chi tiết booking với đầy đủ thông tin liên quan
    """
    try:
        graph = get_falkordb_graph()
        
        query = f"""
        MATCH (u:User)-[:MADE_BOOKING]->(b:Booking {{booking_id: '{booking_id}'}})-[:FOR_PACKAGE]->(p:TourPackage)
        RETURN b.booking_id as booking_id,
               b.number_of_people as number_of_people,
               b.total_amount as total_amount,
               b.travel_date as travel_date,
               b.status as status,
               b.special_requests as special_requests,
               b.contact_name as contact_name,
               b.contact_phone as contact_phone,
               b.created_at as created_at,
               b.package_price as package_price,
               u.name as user_name,
               u.phone as user_phone,
               p.package_id as package_id,
               p.name as package_name,
               p.price as price,
               p.duration_days as duration_days,
               p.destination as destination,
               p.departure_location as departure_location
        """
        
        result = graph.query(query)
        
        if not result.result_set or len(result.result_set) == 0:
            return {
                "success": False,
                "error": f"Không tìm thấy booking với ID: {booking_id}"
            }
        
        row = result.result_set[0]
        
        booking_details = {
            "booking_id": row[0],
            "number_of_people": row[1],
            "total_amount": row[2],
            "travel_date": row[3],
            "status": row[4],
            "special_requests": row[5],
            "contact_name": row[6],
            "contact_phone": row[7],
            "created_at": row[8],
            "package_price": row[9],
            "user": {
                "name": row[10],
                "phone": row[11]
            },
            "package": {
                "package_id": row[12],
                "name": row[13],
                "price": row[14],
                "duration_days": row[15],
                "destination": row[16],
                "departure_location": row[17]
            }
        }
        
        logger.info(f"✅ Retrieved booking details for {booking_id} from FalkorDB")
        
        return {
            "success": True,
            "booking": booking_details
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting booking details from FalkorDB: {str(e)}")
        return {
            "success": False,
            "error": f"Lỗi khi lấy chi tiết booking từ FalkorDB: {str(e)}"
        }


def get_database_statistics() -> Dict[str, Any]:
    """
    Lấy thống kê tổng quan về database
    
    Returns:
        Thống kê về số lượng nodes, relationships, và các metrics khác
    """
    try:
        graph = get_falkordb_graph()
        
        stats = {}
        
        # Đếm số lượng mỗi loại node
        node_types = ['User', 'Booking', 'TourPackage', 'Destination', 'Location']
        stats['nodes'] = {}
        
        for node_type in node_types:
            query = f"MATCH (n:{node_type}) RETURN count(n) as count"
            result = graph.query(query)
            if result.result_set:
                stats['nodes'][node_type] = result.result_set[0][0]
        
        # Đếm relationships
        stats['relationships'] = {}
        rel_types_query = "CALL db.relationshipTypes()"
        rel_types_result = graph.query(rel_types_query)
        
        if rel_types_result.result_set:
            for row in rel_types_result.result_set:
                rel_type = row[0]
                count_query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
                count_result = graph.query(count_query)
                if count_result.result_set:
                    stats['relationships'][rel_type] = count_result.result_set[0][0]
        
        # Thống kê booking
        stats['bookings'] = {}
        
        # Booking by status
        status_query = """
        MATCH (b:Booking)
        RETURN b.status as status, count(b) as count
        """
        status_result = graph.query(status_query)
        if status_result.result_set:
            stats['bookings']['by_status'] = {}
            for row in status_result.result_set:
                status = row[0] or 'unknown'
                count = row[1]
                stats['bookings']['by_status'][status] = count
        
        # Total revenue
        revenue_query = """
        MATCH (b:Booking)
        RETURN sum(b.total_amount) as total, avg(b.total_amount) as average
        """
        revenue_result = graph.query(revenue_query)
        if revenue_result.result_set and revenue_result.result_set[0][0] is not None:
            stats['bookings']['total_revenue'] = revenue_result.result_set[0][0]
            stats['bookings']['average_revenue'] = revenue_result.result_set[0][1]
        
        logger.info("✅ Retrieved database statistics from FalkorDB")
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting statistics from FalkorDB: {str(e)}")
        return {
            "success": False,
            "error": f"Lỗi khi lấy thống kê từ FalkorDB: {str(e)}"
        }
