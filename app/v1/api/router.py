"""
Main API Router
"""
from fastapi import APIRouter
from .endpoints import chat, chat_rooms, agent, health, auth, tour_packages, bookings, booking_management, promotions, payments, reports, travel_news, admin_recommendations, news_agent, admin_users, users, reviews, admin_agent, notifications, favorites

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(chat_rooms.router, prefix="/chat", tags=["Chat Rooms"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tour_packages.router, prefix="/tour-packages", tags=["Tour Packages"])
api_router.include_router(admin_recommendations.router, prefix="/tour-packages", tags=["Admin Recommendations"])
api_router.include_router(booking_management.router, prefix="/bookings", tags=["Booking Management"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(promotions.router, prefix="/promotions", tags=["Promotions"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports & Analytics"])
api_router.include_router(travel_news.router, prefix="/travel-news", tags=["Travel News"])
api_router.include_router(news_agent.router, prefix="/news-agent", tags=["News Agent"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
api_router.include_router(users.router, prefix="/users", tags=["User Profile"])
api_router.include_router(admin_users.router, prefix="/admin/users", tags=["Admin - User Management"])
api_router.include_router(admin_agent.router, prefix="/admin/agent", tags=["Admin - AI Agent"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(favorites.router, prefix="/favorites", tags=["Favorites"])

