from app.api.routes import applications, catalog, checklists, matching, outreach, profile

router = catalog.router
router.include_router(profile.router)
router.include_router(matching.router)
router.include_router(applications.router)
router.include_router(outreach.router)
router.include_router(checklists.router)
