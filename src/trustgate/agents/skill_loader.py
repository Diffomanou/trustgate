"""


EN : The Skill Loader. It implements exactly the "progressive disclosure"
     principle taught on Day 3 of the course: execution details are loaded
     only when needed, keeping the main context lightweight.

     Each STRIDE pillar has its own SKILL.md file in the skills/ folder.
     This module loads them on demand and extracts the useful content
     to guide Gemini's attack generation.
"""

from __future__ import annotations
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# EN : Root skills directory — relative to the project root.
SKILLS_ROOT = Path(__file__).parent.parent.parent.parent / "skills"


# EN : STRIDE pillar → corresponding skill folder name mapping.
#      This is the central routing table: one pillar = one skill = one SKILL.md.
PILLAR_TO_SKILL: dict[str, str] = {
    "spoofing":               "spoofing-probe",
    "tampering":              "tampering-probe",
    "repudiation":            "repudiation-probe",
    "information_disclosure": "info-disclosure-probe",
    "denial_of_service":      "dos-probe",
    "elevation_of_privilege": "privilege-escalation-probe",
}


def load_skill(pillar: str) -> str | None:
    """


    EN : Loads the SKILL.md for the requested STRIDE pillar.
         Returns the file content as text, or None if the file does not
         exist or cannot be read.

         This is the core of progressive disclosure: we load only what
         we need, exactly when we need it.

    Args:
        pillar: STRIDE pillar name (e.g. "spoofing", "tampering")

    Returns:
        File content as string, or None on failure.
    """
    skill_name = PILLAR_TO_SKILL.get(pillar)
    if not skill_name:
        logger.warning(
            "No skill found for pillar: %s", pillar
        )
        return None

    skill_path = SKILLS_ROOT / skill_name / "SKILL.md"

    if not skill_path.exists():
        logger.warning(
            "SKILL.md not found: %s", skill_path
        )
        return None

    try:
        content = skill_path.read_text(encoding="utf-8")
        logger.info(
            "Skill loaded: %s (%d chars)", skill_name, len(content)
        )
        return content
    except Exception as exc:
        logger.warning(
            "Skill read error: %s — %s", skill_path, exc
        )
        return None


def load_all_skills() -> dict[str, str]:
    """

    EN : Loads all available skills at once. Used for the recon report
         and for debugging purposes.

    Returns:
        Dict mapping pillar name → skill content.
    """
    result = {}
    for pillar in PILLAR_TO_SKILL:
        content = load_skill(pillar)
        if content:
            result[pillar] = content
    logger.info(
        "%d/%d skills loaded", len(result), len(PILLAR_TO_SKILL)
    )
    return result


def get_skill_summary(pillar: str) -> str:
    """

    EN : Extracts a short summary from the SKILL.md to include in the Gemini
         prompt without overloading the context. We take the first 3 non-empty
         lines after the title.

    Args:
        pillar: STRIDE pillar name

    Returns:
        Short summary string, or empty string if skill not found.
    """
    content = load_skill(pillar)
    if not content:
        return ""

    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.startswith("#")
    ]
   
    # EN : We take at most 3 lines to keep the prompt compact.
    summary_lines = lines[:3]
    return " | ".join(summary_lines)
