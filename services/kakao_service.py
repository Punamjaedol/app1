import httpx
from typing import Tuple

KAKAO_REST_API_KEY = "f5f657927874c4517a98482e9bd5a412"  # REST API 키 (JS 키 아님!)

async def reverse_geocode_mock(lat: float, lng: float) -> Tuple[str, str]:
    """Mock fallback if API fails"""
    mock_places = ["Cozy Cafe", "Romantic Restaurant", "Sunny Park", "Movie Theater", "Shopping Mall"]
    idx = int((abs(lat) + abs(lng)) * 10000) % len(mock_places)
    return mock_places[idx], f"Near {lat:.4f}, {lng:.4f}"

async def reverse_geocode_kakao(lat: float, lng: float) -> Tuple[str, str]:
    """
    카카오 좌표 → 주소 변환 API (정확한 reverse geocoding)
    """
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
    }
    params = {
        "x": lng,  # 경도
        "y": lat,  # 위도
        "input_coord": "WGS84"
    }

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, headers=headers, params=params)
            data = r.json()

            if data.get("documents"):
                doc = data["documents"][0]
                
                # 도로명 주소 우선, 없으면 지번 주소
                road = doc.get("road_address")
                addr = doc.get("address")
                
                if road:
                    name = road.get("building_name") or road.get("road_name", "")
                    address = road.get("address_name", "")
                else:
                    name = addr.get("region_3depth_name", "")
                    address = addr.get("address_name", "")

                return name or address, address

        except Exception as e:
            print("Kakao API error:", e)

    return await reverse_geocode_mock(lat, lng)