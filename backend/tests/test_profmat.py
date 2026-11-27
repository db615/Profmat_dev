from app.seed import seed_database

PASSWORD = "long test password"


def register(client, email: str = "student@example.com") -> dict[str, str]:
    response = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_seed_is_idempotent(session):
    first = seed_database(session)
    second = seed_database(session)
    assert first == second
    assert first["countries"] == 6
    assert first["universities"] == 8
    assert first["professors"] == 17
    assert first["programs"] == 11


def test_catalog_serializes_cleanly(seeded, client):
    countries = client.get("/api/v1/countries")
    assert countries.status_code == 200
    payload = countries.json()
    assert {country["country_code"] for country in payload} >= {"US", "GB", "DE"}
    assert all("_sa_instance_state" not in country for country in payload)

    universities = client.get("/api/v1/universities").json()
    assert len(universities) == 8
    university = next(item for item in universities if item["name"] == "Stanford University")
    assert client.get(f"/api/v1/universities/{university['id']}").status_code == 200
    assert len(client.get(f"/api/v1/universities/{university['id']}/professors").json()) >= 1
    assert len(client.get(f"/api/v1/universities/{university['id']}/programs").json()) >= 1
    assert len(client.get("/api/v1/news").json()) == 3
    assert client.get("/api/v1/countries/US/visas").json()[0]["visa_type"] == "F-1 Student Visa"


def test_professor_matches_use_single_fk(seeded, client):
    headers = register(client)
    profile = client.put(
        "/api/v1/me/research-profile",
        json={"research_interests": "machine learning computer vision", "skills": "python"},
        headers=headers,
    )
    assert profile.status_code == 200
    assert profile.json()["research_interests"] == "machine learning computer vision"

    preference = client.post(
        "/api/v1/me/preferences", json={"country_code": "US", "priority": 1}, headers=headers
    )
    assert preference.status_code == 201

    generated = client.post("/api/v1/matches/generate", json={}, headers=headers)
    assert generated.status_code == 201
    matches = generated.json()
    assert matches
    for match in matches:
        populated = [
            match[field]
            for field in ("professor_id", "university_id", "course_program_id", "funding_id")
            if match[field]
        ]
        assert len(populated) == 1
        assert match["algorithm_version"] == "basic-v1"
    assert matches[0]["match_score"] >= matches[-1]["match_score"]

    listed = client.get("/api/v1/matches", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == len(matches)

    refreshed = client.post("/api/v1/matches/generate", json={}, headers=headers)
    assert refreshed.status_code == 201
    assert len(refreshed.json()) == len(matches)


def test_profmat_requires_authentication(client):
    assert client.get("/api/v1/matches").status_code == 401
    assert client.post("/api/v1/matches/generate", json={}).status_code == 401


def test_profile_and_application_flow(seeded, client):
    headers = register(client)
    academic = client.put(
        "/api/v1/me/academic-profile",
        json={"degree_level": "BSc", "field_of_study": "Computer Science", "graduation_year": 2025},
        headers=headers,
    )
    assert academic.status_code == 200
    assert academic.json()["graduation_year"] == 2025

    university = client.get("/api/v1/universities").json()[0]
    program = client.get(f"/api/v1/universities/{university['id']}/programs").json()[0]
    application = client.post(
        "/api/v1/applications",
        json={
            "university_id": university["id"],
            "course_program_id": program["id"],
            "stage": "SHORTLISTED",
        },
        headers=headers,
    )
    assert application.status_code == 201
    application_id = application.json()["id"]

    moved = client.patch(
        f"/api/v1/applications/{application_id}/stage",
        json={"stage": "SUBMITTED"},
        headers=headers,
    )
    assert moved.status_code == 200
    assert moved.json()["stage"] == "SUBMITTED"
    assert moved.json()["submitted_at"]
