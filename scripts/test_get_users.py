import httpx

r = httpx.get('http://localhost:8000/users/', timeout=10.0)
print(r.status_code)
print(r.json()[:10])
