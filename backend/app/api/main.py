from fastapi import APIRouter

from app.api.routes import auth, email, users, utils
from app.api.routes.dmca import cases as dmca_cases
from app.api.routes.dmca import emails as dmca_emails
from app.api.routes.dmca import legal_grounds as dmca_legal_grounds
from app.api.routes.dmca import profiles as dmca_profiles
from app.api.routes.dmca import recipients as dmca_recipients

api_router = APIRouter()
api_router.include_router(utils.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(email.router)
api_router.include_router(dmca_recipients.router)
api_router.include_router(dmca_legal_grounds.router)
api_router.include_router(dmca_profiles.router)
api_router.include_router(dmca_cases.router)
api_router.include_router(dmca_emails.router)
