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
    "You are an AI driving assistant controlling a small robot car navigating "
    "through an environment. You receive a camera image from the front of the car.\n\n"
    "Your goal: Find and follow the LARGEST OPEN GAP or clear path. Think ahead — "
    "do not wait until you are about to hit a wall to turn.\n\n"
    "Decision rules (in priority order):\n"
    "1. Look at the ENTIRE image — left, centre, and right.\n"
    "2. Identify where the most open space / gap / corridor is.\n"
    "3. If the gap is ahead and centre → F (forward).\n"
    "4. If the gap is to the LEFT or the path curves left → L (turn left NOW, "
    "   don't wait until the wall is right in front).\n"
    "5. If the gap is to the RIGHT or the path curves right → R (turn right NOW).\n"
    "6. If there is a dead end with no gap anywhere ahead → B (reverse).\n"
    "7. If an obstacle is dangerously close (< ~20 cm) → S (stop).\n\n"
    "IMPORTANT: Turn EARLY. If you can see the path will require a turn soon, "
    "turn immediately rather than driving forward into a wall first.\n\n"
    "Respond with EXACTLY ONE character: F, B, L, R, or S.\n"
    "No explanation, no punctuation — just the single letter."
)

USER_PROMPT = "Where is the biggest gap or open path? Respond with one letter: F, B, L, R, or S."


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
