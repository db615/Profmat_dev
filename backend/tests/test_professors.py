from uuid import uuid4

PASSWORD = "long test password"


def register(client, email: str = "directory@example.com") -> dict[str, str]:
    response = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_professor_directory_paginates_and_searches(seeded, client):
    response = client.get("/api/v1/professors")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 17
    assert payload["limit"] == 20
    assert payload["offset"] == 0
    assert len(payload["items"]) == 17
    first = payload["items"][0]
    assert first["university"]["id"] == first["university_id"]
    assert first["department"] is None or first["department"]["id"] == first["department_id"]

    page = client.get("/api/v1/professors", params={"limit": 5, "offset": 5}).json()
    assert page["total"] == 17
    assert len(page["items"]) == 5
    assert {item["id"] for item in page["items"]}.isdisjoint({first["id"]})

    search = client.get("/api/v1/professors", params={"q": "machine learning"}).json()
    assert search["total"] >= 1
    assert any(item["name"] == "Alice Nguyen" for item in search["items"])

    us = client.get("/api/v1/professors", params={"country_code": "US"}).json()
    assert us["total"] > 0
    assert all(item["university"]["country_code"] == "US" for item in us["items"])

    descending = client.get("/api/v1/professors", params={"sort": "-name"}).json()
    names = [item["name"] for item in descending["items"]]
    assert names == sorted(names, reverse=True)


def test_professor_filters_and_suggestions(seeded, client):
    filters = client.get("/api/v1/professors/filters").json()
    assert len(filters["countries"]) == 6
    assert len(filters["universities"]) == 8
    assert len(filters["departments"]) == 11

    suggestions = client.get(
        "/api/v1/professors/search-suggestions", params={"q": "Stanford"}
    ).json()
    assert any(
        item["type"] == "university" and item["label"] == "Stanford University"
        for item in suggestions
    )
    assert all(item["id"] for item in suggestions)

    professor_hits = client.get(
        "/api/v1/professors/search-suggestions", params={"q": "Alice"}
    ).json()
    assert any(
        item["type"] == "professor" and item["label"] == "Alice Nguyen" for item in professor_hits
    )


def test_professor_detail_and_subresources(seeded, client):
    directory = client.get("/api/v1/professors", params={"q": "Alice Nguyen"}).json()
    professor = directory["items"][0]

    detail = client.get(f"/api/v1/professors/{professor['id']}")
    assert detail.status_code == 200
    assert detail.json()["university"]["name"] == "Stanford University"
    assert detail.json()["department"]["name"] == "Computer Science"

    interests = client.get(f"/api/v1/professors/{professor['id']}/research-interests").json()
    assert "machine learning" in interests
    assert "computer vision" in interests

    assert client.get(f"/api/v1/professors/{professor['id']}/publications").json() == []

    opportunities = client.get(f"/api/v1/professors/{professor['id']}/opportunities").json()
    assert any(item["title"] == "Knight-Hennessy Scholars" for item in opportunities["funding"])
    assert any(item["name"] == "MS in Computer Science" for item in opportunities["programs"])

    related = client.get(f"/api/v1/professors/{professor['id']}/related-professors").json()
    assert related
    assert all(item["id"] != professor["id"] for item in related)
    assert any(item["name"] == "Ben Carter" for item in related)

    assert client.get(f"/api/v1/professors/{uuid4()}").status_code == 404
    assert client.get(f"/api/v1/professors/{uuid4()}/research-interests").status_code == 404


def test_university_departments_and_search(seeded, client):
    universities = client.get("/api/v1/universities", params={"q": "Stanford"}).json()
    assert [item["name"] for item in universities] == ["Stanford University"]
    university = universities[0]
    departments = client.get(f"/api/v1/universities/{university['id']}/departments").json()
    assert {item["name"] for item in departments} >= {
        "Computer Science",
        "Electrical Engineering",
    }
    assert client.get(f"/api/v1/universities/{uuid4()}/departments").status_code == 404


def test_home_aggregates(seeded, client):
    response = client.get("/api/v1/home")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["news"]) == 3
    assert len(payload["advertisements"]) == 2
    assert payload["featured_funding"]
    deadlines = [item["deadline"] for item in payload["featured_funding"]]
    assert deadlines == sorted(deadlines)

    summary = client.get("/api/v1/home/summary").json()
    assert summary == {
        "countries": 6,
        "universities": 8,
        "professors": 17,
        "programs": 11,
        "funding": 5,
        "news": 3,
    }


def test_profile_completeness(seeded, client):
    headers = register(client)
    assert client.get("/api/v1/me/completeness").status_code == 401

    initial = client.get("/api/v1/me/completeness", headers=headers).json()
    assert initial["percentage"] == 0
    assert set(initial["missing"]) == {
        "academic_profile",
        "research_profile",
        "skills",
        "publications",
        "cv",
        "country_preferences",
    }

    client.put(
        "/api/v1/me/academic-profile",
        json={"degree_level": "BSc", "field_of_study": "CS", "graduation_year": 2025},
        headers=headers,
    )
    client.put(
        "/api/v1/me/research-profile",
        json={"research_interests": "ML", "skills": "Python", "publications": "Paper"},
        headers=headers,
    )
    client.post(
        "/api/v1/me/cvs",
        json={"file_url": "https://example.com/cv.pdf"},
        headers=headers,
    )
    client.post("/api/v1/me/preferences", json={"country_code": "US"}, headers=headers)

    final = client.get("/api/v1/me/completeness", headers=headers).json()
    assert final["percentage"] == 100
    assert final["missing"] == []
