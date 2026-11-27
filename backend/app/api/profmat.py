from fastapi import APIRouter, Depends

from app.api.dependencies import require_browser_protection
from app.api.routes import applications, catalog, checklists, matching, outreach, profile

router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_browser_protection)],
)
router.include_router(catalog.router)
router.include_router(profile.router)
router.include_router(matching.router)
router.include_router(applications.router)
router.include_router(outreach.router)
router.include_router(checklists.router)
