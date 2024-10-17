import pytest
from fastapi import status


@pytest.mark.anyio
async def test_show_image(client, testfs):
    with open("tests/sample_avatar.jpeg", "rb") as f:
        file_id = await testfs.upload_from_stream(
            "sample_avatar.jpeg", f, metadata={"content_type": "image/jpeg"}
        )

    response = await client.get(f"/images/{file_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers.get("content-type") == "image/jpeg"

    assert response.content