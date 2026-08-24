import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1200
HEIGHT = 675
BACKGROUND = "#0b1020"
PANEL = "#111827"
TEXT = "#d1d5db"
MUTED = "#8b98aa"
GREEN = "#34d399"
CYAN = "#67e8f9"
FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")

DEMO_LINES = [
    ("$ ./demo.sh", GREEN),
    ("CareerForge — deterministic agent demo", CYAN),
    ("AI agents that forge career data into action.", TEXT),
    ("", TEXT),
    ("1. Triage an interview invitation", GREEN),
    ("   Interview Invitation · confidence=0.9 · Notion write=planned", TEXT),
    ("", TEXT),
    ("2. Evaluate a platform role", GREEN),
    ("   Principal Platform Engineer · fit=87/100 · priority=High", TEXT),
    ("", TEXT),
    ("3. Tailor the resume", GREEN),
    ("   Generated truthful role-specific tailoring notes", TEXT),
    ("", TEXT),
    ("No credentials. No network calls. No writes.", MUTED),
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if FONT_PATH.exists():
        return ImageFont.truetype(str(FONT_PATH), size=size)
    return ImageFont.load_default()


def render_frame(visible_lines: int) -> Image.Image:
    """Renders one exact terminal-demo frame."""

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((54, 42, WIDTH - 54, HEIGHT - 42), radius=18, fill=PANEL)
    draw.ellipse((84, 70, 98, 84), fill="#fb7185")
    draw.ellipse((108, 70, 122, 84), fill="#fbbf24")
    draw.ellipse((132, 70, 146, 84), fill=GREEN)
    draw.text((WIDTH - 235, 66), "career-forge", font=_font(19), fill=MUTED)

    y = 118
    regular = _font(23)
    for line, color in DEMO_LINES[:visible_lines]:
        draw.text((86, y), line, font=regular, fill=color)
        y += 37
    return image


def build_gif(output: Path) -> None:
    """Builds a 34-second loop from the verified deterministic demo output."""

    reveal_counts = [1, 3, 6, 9, 12, 14]
    frames = [render_frame(count) for count in reveal_counts]
    durations_ms = [2_000, 4_000, 6_000, 6_000, 6_000, 10_000]
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=durations_ms,
        loop=0,
        optimize=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the CareerForge terminal demo GIF.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/assets/career-forge-demo.gif"),
    )
    args = parser.parse_args()
    build_gif(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
