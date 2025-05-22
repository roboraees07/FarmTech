import requests
import base64
from datetime import datetime

def upload_vegetable_data(
    endpoint_url: str,
    image_path: str,
    weight: float,
    veg_name: str,
    date_time: datetime | str
) -> dict:
    """
    Uploads a vegetable image and metadata to the Firebase Cloud Function.

    :param endpoint_url: Full URL of your uploadVegetableData function. 
    :param image_path: Path to the local image file to upload.
    :param weight: Weight of the vegetable (will be sent as string).
    :param veg_name: Name of the vegetable.
    :param date_time: A datetime or ISO‑format string representing the timestamp.
    :return: Parsed JSON response from the function.
    :raises: HTTPError or Exception on bad response.
    """
    # 1. Read and encode image
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    image_base64 = base64.b64encode(img_bytes).decode('utf-8')

    # 2. Prepare payload
    if isinstance(date_time, datetime):
        date_time = date_time.isoformat()
    payload = {
        "imageBase64": image_base64,
        "weight": str(weight),
        "vegName": veg_name,
        "dateTime": date_time
    }

    # 3. Send POST
    headers = {"Content-Type": "application/json"}
    resp = requests.post(endpoint_url, json=payload, headers=headers)
    
    # 4. Parse response
    try:
        data = resp.json()
    except ValueError:
        resp.raise_for_status()
    
    if resp.status_code != 200:
        # The function returns { error: "…" } on failure
        error_msg = data.get("error", resp.text)
        raise Exception(f"Upload failed [{resp.status_code}]: {error_msg}")
    
    return data

# Example usage
if __name__ == "__main__":
    from datetime import datetime

    FUNCTION_URL = "https://uploadvegetabledata-6nsemxyzkq-uc.a.run.app"
    try:
        result = upload_vegetable_data(
            FUNCTION_URL,
            image_path="test.png",
            weight=1.25,
            veg_name="Potato",
            date_time=datetime.utcnow()
        )
        print("Upload successful:", result)
    except Exception as e:
        print("Error:", e)
