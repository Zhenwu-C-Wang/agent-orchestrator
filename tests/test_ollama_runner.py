from models.ollama_runner import extract_json_payload


def test_extract_json_payload_from_markdown_fence() -> None:
    raw_text = """
    Here is the result:

    ```json
    {"question":"q","summary":"s","key_points":[],"caveats":[],"sources":[]}
    ```
    """

    payload = extract_json_payload(raw_text)

    assert payload == '{"question":"q","summary":"s","key_points":[],"caveats":[],"sources":[]}'
