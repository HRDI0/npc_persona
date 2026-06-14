import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import TypedDict


DOMAINS = ("location", "world", "npcs", "quests")
STRUCTURED_SOURCE_DIRS = ("npcs", "locations", "quests", "world")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


class RawSection(TypedDict):
    title: str
    heading_level: int
    line_start: int
    text: str


class ClassifiedSection(TypedDict):
    title: str
    domain: str
    heading_level: int
    line_start: int
    reasons: list[str]


class SourceReport(TypedDict):
    path: str
    summary: dict[str, int]
    sections: list[ClassifiedSection]

LOCATION_KEYWORDS = (
    "장소",
    "맵",
    "광장",
    "농장",
    "들판",
    "훈련장",
    "숲 입구",
    "샘터",
    "잡화점",
    "오솔길",
    "뒷골목",
    "창고",
    "분위기",
    "랜드마크",
)
NPC_KEYWORDS = (
    "NPC",
    "인물",
    "민민",
    "리오",
    "루미",
    "로완",
    "촌장",
    "부인",
    "순찰대장",
    "마도사",
    "말투",
    "연대기",
)
QUEST_KEYWORDS = (
    "퀘스트",
    "의뢰",
    "목표",
    "단서",
    "정답",
    "힌트",
    "조사",
    "사건",
    "보상",
    "플레이어",
)
WORLD_KEYWORDS = (
    "세계관",
    "문서 개요",
    "역사",
    "규칙",
    "역할",
    "RBAC",
    "지식 유형",
    "마나",
    "포자",
    "달빛",
    "활용 방향",
    "전체 정리",
)


def split_markdown_sections(text: str) -> list[RawSection]:
    matches = list(HEADING_RE.finditer(text))
    sections: list[RawSection] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        heading_line = text.count("\n", 0, match.start()) + 1
        sections.append(
            {
                "title": match.group(2).strip(),
                "heading_level": len(match.group(1)),
                "line_start": heading_line,
                "text": body,
            }
        )

    return sections


def score_keywords(title: str, body: str, keywords: Iterable[str]) -> int:
    haystack = f"{title}\n{body}"
    title_score = sum(3 for keyword in keywords if keyword in title)
    body_score = sum(1 for keyword in keywords if keyword in haystack)
    return title_score + body_score


def classify_section(title: str, body: str, heading_level: int) -> tuple[str, list[str]]:
    scores = {
        "location": score_keywords(title, body, LOCATION_KEYWORDS),
        "world": score_keywords(title, body, WORLD_KEYWORDS),
        "npcs": score_keywords(title, body, NPC_KEYWORDS),
        "quests": score_keywords(title, body, QUEST_KEYWORDS),
    }

    if heading_level == 1 and title not in {"헤이즐 마을 맵별 스토리", "헤이즐 마을 NPC별 연대기"}:
        if score_keywords(title, body, LOCATION_KEYWORDS) >= 1:
            scores["location"] += 8
        if score_keywords(title, body, NPC_KEYWORDS) >= 1:
            scores["npcs"] += 8

    if "story-chunk" in body or "RAG Chunk" in body:
        scores["npcs"] += 4
    if "quest_id" in body or "퀘스트" in body:
        scores["quests"] += 2
    if "장소 개요" in body or "맵 분위기" in body:
        scores["location"] += 5
    if title in {"문서 개요", "전체 정리", "캐릭터별 정보 차이", "맵별 스토리 활용 방향"}:
        scores["world"] += 6

    domain = max(DOMAINS, key=lambda item: (scores[item], -DOMAINS.index(item)))
    reasons = [f"{key}:{scores[key]}" for key in DOMAINS if scores[key] > 0]
    if not reasons:
        reasons = ["keyword:0"]
    return domain, reasons


def classify_path(path: Path) -> SourceReport:
    text = path.read_text(encoding="utf-8")
    sections: list[ClassifiedSection] = []
    summary = {domain: 0 for domain in DOMAINS}

    for raw_section in split_markdown_sections(text):
        title = raw_section["title"]
        body = raw_section["text"]
        heading_level = raw_section["heading_level"]
        domain, reasons = classify_section(title, body, heading_level)
        summary[domain] += 1
        sections.append(
            {
                "title": title,
                "domain": domain,
                "heading_level": heading_level,
                "line_start": raw_section["line_start"],
                "reasons": reasons,
            }
        )

    return {
        "path": str(path),
        "summary": summary,
        "sections": sections,
    }


def build_report(source_dir: Path, raw_paths: list[Path]) -> dict[str, object]:
    sources = [classify_path(path) for path in sorted(raw_paths, key=lambda item: str(item))]
    summary = {domain: 0 for domain in DOMAINS}

    for source in sources:
        for domain in DOMAINS:
            summary[domain] += source["summary"][domain]

    return {
        "mode": "review_only",
        "source_dir": str(source_dir),
        "summary": summary,
        "sources": sources,
    }


def is_relative_to(child: Path, parent: Path) -> bool:
    child_parts = child.resolve().parts
    parent_parts = parent.resolve().parts
    return child_parts[: len(parent_parts)] == parent_parts


def assert_review_output_path(output_path: Path, source_dir: Path) -> None:
    source_root = source_dir
    protected_dirs = [source_root / folder for folder in STRUCTURED_SOURCE_DIRS]
    if any(is_relative_to(output_path, protected_dir) for protected_dir in protected_dirs):
        raise ValueError(f"review report output cannot be inside structured source folders: {output_path}")


def write_report(report: dict[str, object], output_path: Path, *, overwrite: bool = False) -> None:
    source_dir_value = report.get("source_dir", "rsc/data")
    source_dir = Path(source_dir_value) if isinstance(source_dir_value, str) else Path("rsc/data")
    assert_review_output_path(output_path, source_dir)

    if output_path.exists() and not overwrite:
        raise FileExistsError(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    _ = temp_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _ = temp_path.replace(output_path)


def default_raw_paths(source_dir: Path) -> list[Path]:
    return sorted(source_dir.glob("hazel_village_*.md"), key=lambda item: item.name)


def parse_args(argv: list[str]) -> tuple[Path, Path, bool, list[Path]]:
    source_dir = Path("rsc/data")
    output = Path("output/reports/story_source_classification_review.json")
    overwrite = False
    raw_paths: list[Path] = []
    index = 0

    while index < len(argv):
        arg = argv[index]
        if arg == "--source-dir":
            index += 1
            source_dir = Path(argv[index])
        elif arg == "--output":
            index += 1
            output = Path(argv[index])
        elif arg == "--overwrite":
            overwrite = True
        elif arg in {"-h", "--help"}:
            print("Usage: scripts/story_pipeline/classify_story_sources.py [--source-dir PATH] [--output PATH] [--overwrite] [RAW.md ...]")
            raise SystemExit(0)
        else:
            raw_paths.append(Path(arg))
        index += 1

    return source_dir, output, overwrite, raw_paths


def main() -> None:
    source_dir, output, overwrite, raw_paths_arg = parse_args(sys.argv[1:])
    raw_paths = raw_paths_arg or default_raw_paths(source_dir)
    report = build_report(source_dir, raw_paths)
    write_report(report, output, overwrite=overwrite)
    print(f"Wrote review-only classification report: {output}")


if __name__ == "__main__":
    main()
