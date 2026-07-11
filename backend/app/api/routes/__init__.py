from fastapi import APIRouter

from app.api.routes import applications, members

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(applications.router)
api_router.include_router(members.router)

# Future routers will be added here as features are built:
# from app.api.routes import events, reports, auth, settings
# api_router.include_router(events.router)
# api_router.include_router(reports.router)
# api_router.include_router(auth.router)
# api_router.include_router(settings.router)
