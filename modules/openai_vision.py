from openai import AzureOpenAI
import os
import base64

# ---------------------------------------------------------------------------
# Cached client -- reused across calls (saves ~200-400ms connection setup)
# ---------------------------------------------------------------------------
_client = None


def _get_client():
    """Get or create cached Azure OpenAI client."""
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_key=os.environ['OPENAI_API_KEY'],
            api_version=os.environ['API_VERSION'],
            azure_endpoint=os.environ['OPENAI_API_BASE'],
            organization=os.environ['OPENAI_ORGANIZATION']
        )
    return _client


SYSTEM_PROMPT = (
    "You are an AI driving assistant controlling a small robot car. "
    "You will receive a camera image from the front of the car. "
    "Based on what you see, respond with EXACTLY ONE character — the best "
    "driving command:\n"
    "  F = move forward (path is clear ahead)\n"
    "  B = move backward (dead end or need to reverse)\n"
    "  L = turn left\n"
    "  R = turn right\n"
    "  S = stop (obstacle too close or unsafe)\n\n"
    "Rules:\n"
    "- Respond with ONLY the single letter. No explanation, no punctuation.\n"
    "- Prioritise safety: if unsure, respond S.\n"
)

USER_PROMPT = "What should the car do? Respond with one letter: F, B, L, R, or S."


def get_driving_command(image_path=None):
    """Send an image to the LLM and return a single driving command letter (F/B/L/R/S).

    Args:
        image_path: Optional path to an image file. Defaults to images/image.jpg.
    """
    if image_path is None:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        image_path = os.path.join(project_root, 'images', 'image.jpg')

    with open(image_path, 'rb') as f:
        imagedata = base64.b64encode(f.read()).decode('ascii')

    client = _get_client()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": USER_PROMPT},
            {"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{imagedata}"
            }}
        ]}
    ]

    response = client.chat.completions.create(
        model=os.environ['MODEL'],
        messages=messages,
        # temperature=0.0,
        # max_tokens=1,
    )

    raw = response.choices[0].message.content.strip().upper()
    # Guarantee we only return a valid command
    return raw if raw in ('F', 'B', 'L', 'R', 'S') else 'S'


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    load_dotenv(os.path.join(project_root, '.env'))

    if len(sys.argv) < 2:
        print("Usage: python modules/openai_vision.py <image_path>")
        print("  e.g. python modules/openai_vision.py test_images/hallway.jpg")
        sys.exit(1)

    img = sys.argv[1]
    if not os.path.isfile(img):
        print(f"File not found: {img}")
        sys.exit(1)

    cmd = get_driving_command(image_path=img)
    print(f"LLM says: {cmd}")
