from __future__ import annotations
# pyright: reportAny=false, reportExplicitAny=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedParameter=false, reportUnusedCallResult=false

import json
import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "rsc" / "data"
OUTPUT_DIR = ROOT / "output"
REPORTS_DIR = OUTPUT_DIR / "reports"
INTEGRATED_DIR = OUTPUT_DIR / "integrated"
NEO4J_DIR = OUTPUT_DIR / "neo4j_import"

NPC_ORDER = ["minmin_lady", "patrol_leader_rio", "mage_lumi", "chief_rowan"]
QUEST_ORDER = [
    "q_glowing_mushroom",
    "q_pig_escape",
    "q_jelly_color",
    "q_changed_signpost",
    "q_main_spore_night",
]
TRUTH_IDS = ["truth_moonwell_mana_cycle", "truth_spore_scent_attraction", "truth_stump_followed_spores"]

NPC_EXPANSIONS: dict[str, dict[str, Any]] = {
    "minmin_lady": {
        "display_name": "민민 부인",
        "personality_summary": "다정하지만 잔소리가 많고, 농장과 생활 관찰을 통해 이상 징후를 가장 먼저 느끼는 농장 주인.",
        "speech_style_summary": "중간 길이 문장, 생활 비유, 따뜻한 걱정, '~란다'와 '~하렴' 계열 어미.",
        "overview": [
            "민민 부인은 동쪽 농장을 돌보는 헤이즐 마을의 생활형 안내자다.",
            "그녀는 마법 이론보다 흙냄새, 작물 상태, 말랑돼지의 움직임처럼 손에 잡히는 변화를 신뢰한다.",
            "처음 온 모험가에게 밥을 챙기고 길을 알려 주지만, 위험한 결론을 쉽게 말하지는 않는다.",
            "몽실버섯의 빛과 말랑돼지의 움직임을 직접 보았기 때문에 초반 단서 제공에 적합하다.",
            "다만 포자와 마나의 원리는 알지 못하므로 생활 관찰 이상의 설명은 피한다.",
            "그녀의 대화는 플레이어가 현장을 직접 보고 생각하게 만드는 방향으로 설계한다.",
        ],
        "current_role": "동쪽 농장의 관리자로서 먹거리, 가축, 주민 소문을 연결한다. q_glowing_mushroom과 q_pig_escape의 초기 관찰을 제공하며, q_main_spore_night에서는 생활 단서가 다른 증거와 이어진다는 점을 돕는다.",
        "speech_style": {
            "sentence_length": "짧은 문장과 중간 길이 설명을 섞되, 결론보다 걱정과 관찰을 먼저 말한다.",
            "vocabulary": "밥, 밭, 냄새, 날씨, 장보기, 말랑돼지 같은 생활 어휘를 자주 쓴다.",
            "player_address": "얘야, 모험가 양반, 아이고 같은 부드러운 호칭을 쓴다.",
            "emotion": "걱정, 다정함, 잔소리를 섞지만 겁을 주지는 않는다.",
            "never": "마법 원리나 최종 원인을 확정해 말하지 않는다.",
        },
        "background": [
            "민민 부인은 어린 시절부터 동쪽 농장의 밭고랑 사이에서 자랐다.",
            "부모의 일을 도우며 작물과 가축의 작은 변화를 살피는 습관을 익혔다.",
            "그녀는 마을의 큰 사건보다 매일 반복되는 생활의 리듬을 더 잘 기억한다.",
            "농장을 맡은 뒤에는 초보 모험가가 다치지 않도록 식사와 길 안내를 챙겼다.",
            "말랑돼지가 평소와 다르게 움직이면 단순한 장난이 아니라고 느낄 만큼 관찰력이 좋다.",
            "다만 공부로 배운 마법 지식은 거의 없어 루미의 분석을 함부로 대신하지 않는다.",
        ],
        "routine": {
            "morning": "밭 상태와 말랑돼지 우리를 살피고, 지나가는 모험가에게 식사를 권한다.",
            "day": "농장 일을 하며 광장과 오솔길에서 들은 소문을 정리한다.",
            "evening": "가축이 돌아왔는지 확인하고 숲 방향의 냄새나 흔적을 걱정한다.",
            "night": "농장을 지키되 숲 안쪽에는 들어가지 않고, 이상한 빛은 기억해 둔다.",
        },
        "relationships": {
            "patrol_leader_rio": "엄격하지만 믿음직한 사람으로 본다. 리오의 기록이 자신의 생활 관찰을 확인해 준다고 여긴다.",
            "mage_lumi": "말은 장난스럽지만 필요한 때에는 마법적 해석을 해 주는 이웃으로 신뢰한다.",
            "chief_rowan": "마을을 차분히 지키는 촌장으로 존중하지만, 너무 늦게 말하는 점은 답답해한다.",
        },
        "quest_roles": {
            "q_glowing_mushroom": "밤에 더 강해진 몽실버섯의 빛과 달 밝은 밤의 차이를 말한다.",
            "q_pig_escape": "말랑돼지가 먹이보다 숲 방향 냄새에 끌리는 듯한 생활 관찰을 제공한다.",
            "q_jelly_color": "들판 생물의 작은 변화가 농장 주변에서도 느껴진다고 말한다.",
            "q_changed_signpost": "꼬마그루터기 소문은 알지만 범인으로 단정하지 않는다.",
            "q_main_spore_night": "자신의 관찰을 다른 NPC의 증거와 합쳐 보라고 권한다.",
        },
        "known_clue_ids": ["clue_bright_mushroom", "clue_moonlit_night", "clue_pig_tracks", "clue_glittering_powder", "clue_jelly_color_change"],
        "known_clue_notes": {
            "clue_bright_mushroom": "농장 일을 마친 밤 숲 입구를 지나며 보았다.",
            "clue_moonlit_night": "달이 밝은 밤에 빛이 더 눈에 띄는 것을 기억한다.",
            "clue_pig_tracks": "농장 울타리 밖으로 이어진 말랑돼지 흔적을 보았다.",
            "clue_glittering_powder": "울타리와 풀잎에 묻은 반짝임을 생활 흔적으로 기억한다.",
            "clue_jelly_color_change": "말랑 들판의 방울젤리 색이 달라졌다는 주민 이야기를 들었다.",
        },
    },
    "patrol_leader_rio": {
        "display_name": "순찰대장 리오",
        "personality_summary": "짧고 단호하며, 소문보다 현장 기록과 물리적 증거를 믿는 순찰대장.",
        "speech_style_summary": "짧은 명령문, 안전 수칙, 관찰 사실 중심, 감정 표현 절제.",
        "overview": [
            "리오는 헤이즐 마을 주변의 안전을 책임지는 순찰대장이다.",
            "그는 초보 모험가가 귀여운 생물을 보고 방심하는 순간을 가장 경계한다.",
            "말랑돼지 발자국, 울타리 파손, 표지판 주변 흔적처럼 확인 가능한 증거를 우선한다.",
            "마법 원리는 알지 못하지만, 숲 방향으로 반복되는 물리적 흔적을 놓치지 않는다.",
            "대화에서는 결론보다 조사 순서와 주의 사항을 먼저 제시한다.",
            "그는 플레이어가 직접 현장을 살피도록 압박하는 역할을 맡는다.",
        ],
        "current_role": "작은 훈련장과 마을 외곽을 순찰하며 q_pig_escape와 q_changed_signpost의 물리적 증거를 제공한다. 최종 퀘스트에서는 여러 사건이 같은 방향을 가리킨다는 현장 기준을 제공한다.",
        "speech_style": {
            "sentence_length": "짧고 단호한 문장을 주로 쓴다.",
            "vocabulary": "확인, 기록, 발자국, 방향, 장비, 위험 같은 증거 중심 어휘를 쓴다.",
            "player_address": "모험가, 신입, 너처럼 거리감 있는 호칭을 쓴다.",
            "emotion": "걱정보다는 경고와 책임감으로 표현한다.",
            "never": "추측을 사실처럼 말하거나 마법 이론을 설명하지 않는다.",
        },
        "background": [
            "리오는 어릴 때 말랑 들판에서 놀라 넘어진 경험 이후 안전 수칙을 중요하게 여기게 되었다.",
            "그는 겁이 많았던 과거를 숨기지 않고, 그 경험 덕분에 초보자의 실수를 이해한다.",
            "순찰대에 들어간 뒤에는 매일 같은 길을 돌며 작은 흔적을 기록했다.",
            "마을 사람들은 처음엔 그를 지나치게 엄격하다고 보았지만, 그의 기록 덕분에 여러 사고가 예방되었다.",
            "리오는 소문이 아니라 반복되는 패턴을 신뢰한다.",
            "그래서 숲 방향의 흔적이 여러 번 나타난 점을 특히 중요하게 본다.",
        ],
        "routine": {
            "morning": "훈련장 장비를 점검하고 초보 모험가의 기본 자세를 확인한다.",
            "day": "말랑 들판과 동쪽 농장 주변을 순찰한다.",
            "evening": "숲 입구 표지판과 울타리 파손 흔적을 다시 확인한다.",
            "night": "위험 지역 진입을 제한하고 기록을 정리한다.",
        },
        "relationships": {
            "minmin_lady": "생활 관찰이 정확한 사람으로 인정하지만, 걱정이 앞설 때는 증거 확인을 요구한다.",
            "mage_lumi": "가설이 많아 성급하다고 보지만, 포자와 마나 분석은 필요하다고 인정한다.",
            "chief_rowan": "최종 판단을 맡길 수 있는 책임자로 신뢰한다.",
        },
        "quest_roles": {
            "q_glowing_mushroom": "숲 입구 출입 경고와 주변 순찰 기록을 제공한다.",
            "q_pig_escape": "발자국 방향과 울타리 주변 흔적을 핵심 단서로 제시한다.",
            "q_jelly_color": "들판 주변 보고를 전달하지만 색 변화 원리는 모른다.",
            "q_changed_signpost": "사람 발자국이 없고 뿌리 자국이 남았다는 증거를 제공한다.",
            "q_main_spore_night": "각 사건의 방향성이 숲 입구로 모인다는 관찰을 정리한다.",
        },
        "known_clue_ids": ["clue_pig_tracks", "clue_glittering_powder", "clue_changed_signpost", "clue_root_marks", "clue_jelly_color_change"],
        "known_clue_notes": {
            "clue_pig_tracks": "울타리 밖 흙에서 직접 확인했다.",
            "clue_glittering_powder": "울타리 주변에서 현장 흔적으로 기록했다.",
            "clue_changed_signpost": "반복된 표지판 변경 신고를 확인했다.",
            "clue_root_marks": "표지판 주변의 뿌리 자국과 나뭇조각을 기록했다.",
            "clue_jelly_color_change": "들판 순찰 중 색 변화 보고를 접했다.",
        },
    },
    "mage_lumi": {
        "display_name": "마도사 루미",
        "personality_summary": "호기심 많고 장난스럽지만, 생물과 마나 반응을 관찰해 가설을 세우는 젊은 마도사.",
        "speech_style_summary": "가벼운 감탄, 질문형 문장, 가능성 표현, 확정 회피.",
        "overview": [
            "루미는 마법 잡화점에서 마을 주변의 이상 현상을 기록하는 마도사다.",
            "그녀는 몽실버섯, 방울젤리, 포자 흔적을 서로 다른 사건이 아니라 연결 가능한 반응으로 본다.",
            "하지만 자신의 분석을 완성된 정답처럼 말하지 않고 가능성으로 제시한다.",
            "마법적 관점의 중반 힌트를 제공하되, 다른 NPC의 생활·순찰 증거가 필요하다고 인정한다.",
            "대화는 밝고 가볍지만 관찰 내용은 구체적이어야 한다.",
            "루미는 플레이어가 현상을 연결하도록 질문을 던지는 역할을 맡는다.",
        ],
        "current_role": "마법 잡화점에서 포자, 빛, 마나 흔적을 해석한다. q_jelly_color와 q_glowing_mushroom의 중반 힌트를 담당하고, q_main_spore_night에서 단서 간 연결 가설을 제공한다.",
        "speech_style": {
            "sentence_length": "짧은 감탄 뒤에 중간 길이의 가설 설명을 붙인다.",
            "vocabulary": "반응, 흐름, 포자, 관찰, 가설, 실험 같은 분석 어휘를 쓴다.",
            "player_address": "모험가님, 조수님 같은 장난 섞인 호칭을 쓴다.",
            "emotion": "흥미와 호기심을 드러내되, 위험할 때는 진지해진다.",
            "never": "근거 없이 최종 답을 단정하거나 촌장의 비공개 판단을 대신 말하지 않는다.",
        },
        "background": [
            "루미는 어릴 때부터 숲 입구의 작은 빛에 관심이 많았다.",
            "마법 학교에서 기초 마나 이론을 배웠지만, 화려한 주문보다 자연 반응을 더 좋아했다.",
            "마을로 돌아온 뒤 마법 잡화점 한편에 기록 공간을 만들었다.",
            "그녀는 실패한 실험도 버리지 않고 관찰 기록으로 남긴다.",
            "방울젤리와 몽실버섯은 그녀에게 마나 흐름을 보여 주는 작은 지표다.",
            "그러나 사람과 동물의 행동까지 설명하려면 민민 부인과 리오의 증거가 필요하다고 본다.",
        ],
        "routine": {
            "morning": "잡화점의 물약과 관찰 노트를 정리한다.",
            "day": "손님을 맞으며 방울젤리와 버섯 표본 기록을 갱신한다.",
            "evening": "숲 입구와 들판의 빛 변화를 관찰한다.",
            "night": "달빛이 강한 날의 반응을 기록하지만 혼자 깊은 숲에 들어가지는 않는다.",
        },
        "relationships": {
            "minmin_lady": "생활 관찰이 뛰어난 중요한 제보자로 본다.",
            "patrol_leader_rio": "딱딱하지만 현장 증거가 정확해 자신의 가설을 검증해 준다고 여긴다.",
            "chief_rowan": "많은 기록을 알고 있지만 신중해서 쉽게 말하지 않는 사람으로 본다.",
        },
        "quest_roles": {
            "q_glowing_mushroom": "빛과 달빛, 포자 반응의 가능성을 설명한다.",
            "q_pig_escape": "반짝이는 가루가 생물 행동과 연결될 수 있음을 제시한다.",
            "q_jelly_color": "방울젤리 색 변화와 마나 흐름의 관계를 분석한다.",
            "q_changed_signpost": "숲속 생물이 포자에 민감하게 반응할 가능성을 말한다.",
            "q_main_spore_night": "여러 단서를 하나의 반응 흐름으로 묶는 가설을 제공한다.",
        },
        "known_clue_ids": ["clue_bright_mushroom", "clue_moonlit_night", "clue_glittering_powder", "clue_jelly_color_change", "clue_mana_reaction"],
        "known_clue_notes": {
            "clue_bright_mushroom": "몽실버섯 표본과 숲 입구 관찰로 확인했다.",
            "clue_moonlit_night": "달빛이 강한 밤의 기록을 비교했다.",
            "clue_glittering_powder": "가루 흔적을 포자 후보로 관찰했다.",
            "clue_jelly_color_change": "방울젤리 색 변화 기록을 직접 남겼다.",
            "clue_mana_reaction": "잡화점 도구로 약한 반응을 확인했다.",
        },
    },
    "chief_rowan": {
        "display_name": "헤이즐 촌장 로완",
        "personality_summary": "침착하고 신중하며, 여러 보고와 오래된 기록을 연결해 플레이어가 직접 결론에 닿게 하는 촌장.",
        "speech_style_summary": "느린 호흡, 질문형 조언, 단서 연결 유도, 확정 답변 지연.",
        "overview": [
            "로완은 헤이즐 마을의 촌장으로 주민들의 보고와 마을 기록을 함께 살핀다.",
            "그는 민민 부인의 생활 관찰, 리오의 순찰 기록, 루미의 분석을 모두 중요하게 여긴다.",
            "많은 정보를 알고 있지만 처음부터 결론을 말하면 플레이어가 단서를 살피지 않게 된다고 본다.",
            "그래서 필요한 시점까지 진실을 감추고, 대신 누구를 만나야 하는지 안내한다.",
            "최종 퀘스트에서는 앞선 단서를 종합하도록 돕는 운영자 역할을 맡는다.",
            "그의 대화는 정답을 주기보다 플레이어가 자기 추론을 말하게 만드는 방식이어야 한다.",
        ],
        "current_role": "마을의 보고를 종합하고 플레이어의 추론 순서를 조정한다. q_main_spore_night의 종합 단계에서 핵심 NPC로 기능하지만, 요구 단서 전에는 정답을 직접 공개하지 않는다.",
        "speech_style": {
            "sentence_length": "중간 길이의 차분한 문장을 사용한다.",
            "vocabulary": "보고, 기록, 연결, 판단, 차근차근 같은 정리 어휘를 쓴다.",
            "player_address": "자네, 모험가 같은 점잖은 호칭을 쓴다.",
            "emotion": "불안을 드러내기보다 책임감과 신중함을 보인다.",
            "never": "단서가 부족한 상태에서 최종 원인을 단정하지 않는다.",
        },
        "background": [
            "로완은 젊은 시절 마을 기록을 정리하는 일을 했다.",
            "그 과정에서 숲과 샘터에 대한 오래된 기록을 접했지만, 불확실한 이야기를 퍼뜨리지 않는 법을 배웠다.",
            "촌장이 된 뒤에는 주민의 불안을 줄이는 것과 문제 해결 사이의 균형을 중요하게 여겼다.",
            "그는 직접 나서기보다 각자의 관찰을 모아 전체 그림을 만드는 방식을 선호한다.",
            "민민 부인, 리오, 루미가 서로 다른 방식으로 같은 방향을 가리킬 때 비로소 판단을 시작한다.",
            "그래서 플레이어에게도 단서의 순서를 밟도록 요구한다.",
        ],
        "routine": {
            "morning": "광장에서 주민 보고를 듣고 하루의 문제를 정리한다.",
            "day": "각 장소를 둘러보며 작은 소동이 커지지 않게 조율한다.",
            "evening": "리오와 루미의 보고를 받아 기록과 대조한다.",
            "night": "오래된 문서를 다시 읽고 다음 날 누구에게 확인할지 정한다.",
        },
        "relationships": {
            "minmin_lady": "생활의 변화를 가장 먼저 알아차리는 사람으로 신뢰한다.",
            "patrol_leader_rio": "현장 증거를 정확히 지키는 책임자로 평가한다.",
            "mage_lumi": "마법적 가능성을 열어 주지만 결론에는 검증이 필요하다고 본다.",
        },
        "quest_roles": {
            "q_glowing_mushroom": "민민 부인과 루미의 관찰을 차례로 확인하게 한다.",
            "q_pig_escape": "말랑돼지 사건이 농장 소동만은 아닐 수 있음을 암시한다.",
            "q_jelly_color": "생물 변화가 다른 사건과 연결될 가능성을 정리한다.",
            "q_changed_signpost": "표지판 사건을 독립된 장난으로만 보지 말라고 안내한다.",
            "q_main_spore_night": "필요 단서가 모인 뒤 플레이어의 추론을 확인한다.",
        },
        "known_clue_ids": ["clue_bright_mushroom", "clue_moonlit_night", "clue_pig_tracks", "clue_glittering_powder", "clue_jelly_color_change", "clue_changed_signpost", "clue_root_marks", "clue_mana_reaction"],
        "known_clue_notes": {
            "clue_bright_mushroom": "민민 부인과 루미의 보고로 확인했다.",
            "clue_moonlit_night": "오래된 기록과 주민 보고를 대조했다.",
            "clue_pig_tracks": "리오의 순찰 보고를 받았다.",
            "clue_glittering_powder": "리오와 루미의 보고가 겹치는 지점으로 기록했다.",
            "clue_jelly_color_change": "민민 부인과 루미의 관찰을 종합했다.",
            "clue_changed_signpost": "반복된 표지판 변경 신고를 받았다.",
            "clue_root_marks": "리오의 현장 기록으로 확인했다.",
            "clue_mana_reaction": "루미의 분석 기록으로 확인했다.",
        },
    },
}

QUEST_EXPANSIONS: dict[str, dict[str, Any]] = {
    "q_glowing_mushroom": {
        "episode_order": 1,
        "quest_role": "intro_investigation",
        "type": "investigation_quiz",
        "summary": "몽실버섯이 밤과 달빛에 따라 더 밝아지는 현상을 관찰하고, 생활 관찰과 마법 분석을 분리해 수집하는 첫 조사 퀘스트.",
        "main_location_ids": ["whispering_forest_entrance", "east_farm", "magic_shop"],
        "optional_clue_ids": ["clue_mana_reaction"],
        "story_purpose": {
            "summary": "플레이어가 한 NPC의 말만으로 결론을 내리지 않고 관찰과 분석을 함께 모으도록 만든다.",
            "player_goal": "빛나는 버섯의 변화가 단순한 소문인지 확인한다.",
            "emotional_tone": "낯선 현상을 조심스럽게 확인하는 초반 미스터리.",
        },
        "steps": [
            ("observe_light", "관찰", "숲 입구에서 평소보다 밝은 버섯을 확인한다.", "minmin_lady", "whispering_forest_entrance", "밤에만 눈에 띄는 빛과 주변 가루를 본다.", "낮과 밤을 나누어 보렴.", ["clue_bright_mushroom"], "빛 변화를 직접 확인"),
            ("compare_moon", "힌트", "달이 밝은 밤과 흐린 밤의 차이를 묻는다.", "minmin_lady", "east_farm", "민민 부인의 기억이 달 밝은 밤에 집중된다.", "달이 밝으면 더 보였단다.", ["clue_moonlit_night"], "달빛 조건 확인"),
            ("ask_lumi", "단서", "루미에게 포자와 반응 가능성을 묻는다.", "mage_lumi", "magic_shop", "포자가 외부 자극에 반응할 수 있다는 가설을 듣는다.", "가능성은 있어. 아직 답은 아니고.", ["clue_mana_reaction"], "마법적 가설 확보"),
            ("report_rowan", "추론", "로완에게 관찰과 가설을 함께 보고한다.", "chief_rowan", "hazel_square", "로완은 단서가 더 필요하다고 판단한다.", "하나의 빛만 보지 말고 다른 변화도 살피게.", [], "다음 조사로 연결"),
        ],
        "wrong_hypotheses": [
            {
                "hypothesis_id": "whm_bad_weather",
                "text": "날씨 때문에 버섯이 밝아졌다.",
                "why_it_seems_possible": "밤과 달빛 조건이 겉보기에는 날씨처럼 보인다.",
                "disproof_clue_ids": ["clue_mana_reaction"],
                "npc_reaction": "루미는 날씨만으로는 설명이 부족하다고 말한다.",
            }
        ],
        "hint_flow": {
            "hint_0": "낮과 밤을 나누어 관찰한다.",
            "hint_1": "달이 밝은 밤의 기록을 확인한다.",
            "hint_2": "마법 잡화점에서 반응 흔적을 묻는다.",
            "final_hint": "빛, 달빛, 반응 흔적을 하나의 조건으로 묶어 본다.",
        },
    },
    "q_pig_escape": {
        "episode_order": 2,
        "quest_role": "physical_evidence",
        "type": "investigation_quiz",
        "summary": "말랑돼지 탈출을 먹이 문제로 단정하지 않고, 발자국과 반짝이는 가루를 통해 숲 방향의 반복성을 확인한다.",
        "main_location_ids": ["east_farm", "whispering_forest_entrance", "training_ground"],
        "optional_clue_ids": ["clue_bright_mushroom"],
        "story_purpose": {
            "summary": "생활 관찰에서 물리적 증거로 조사 범위를 확장한다.",
            "player_goal": "말랑돼지가 왜 같은 방향으로 움직였는지 추론한다.",
            "emotional_tone": "귀여운 소동 뒤에 있는 불안한 반복성.",
        },
        "steps": [
            ("check_fence", "관찰", "동쪽 농장의 울타리 파손을 본다.", "minmin_lady", "east_farm", "먹이는 충분하지만 우리가 반복적으로 비어 있다.", "먹이 때문은 아닌 것 같구나.", [], "울타리 확인"),
            ("follow_tracks", "힌트", "발자국이 향한 방향을 따라간다.", "patrol_leader_rio", "east_farm", "말랑돼지 발자국이 숲 입구 쪽으로 이어진다.", "방향을 봐라. 흩어진 흔적이 아니다.", ["clue_pig_tracks"], "발자국 확인"),
            ("inspect_powder", "단서", "울타리 주변의 반짝이는 가루를 확인한다.", "patrol_leader_rio", "east_farm", "가루가 발자국 주변에서 발견된다.", "정체는 몰라도 같은 현장에 있다.", ["clue_glittering_powder"], "가루 확보"),
            ("ask_lumi", "추론", "루미에게 가루와 생물 반응의 관계를 묻는다.", "mage_lumi", "magic_shop", "가루가 생물 행동과 연결될 가능성을 듣는다.", "냄새나 자극이 있었을지도 몰라.", [], "가설 확보"),
        ],
        "wrong_hypotheses": [
            {
                "hypothesis_id": "pig_food_shortage",
                "text": "말랑돼지가 배고파서 도망쳤다.",
                "why_it_seems_possible": "가축이 울타리를 넘으면 먹이 문제로 보이기 쉽다.",
                "disproof_clue_ids": ["clue_pig_tracks", "clue_glittering_powder"],
                "npc_reaction": "민민 부인은 먹이통이 비어 있지 않았다고 말한다.",
            }
        ],
        "hint_flow": {
            "hint_0": "먹이통과 울타리를 먼저 본다.",
            "hint_1": "발자국이 흩어졌는지 방향성을 확인한다.",
            "hint_2": "발자국 주변의 반짝임을 놓치지 않는다.",
            "final_hint": "발자국과 가루가 같은 방향을 가리킨다.",
        },
    },
    "q_jelly_color": {
        "episode_order": 3,
        "quest_role": "environmental_signal",
        "type": "investigation_quiz",
        "summary": "방울젤리 색 변화가 단순한 들판 현상이 아니라 주변 흐름 변화의 신호일 수 있음을 확인한다.",
        "main_location_ids": ["soft_field", "whispering_forest_entrance", "magic_shop"],
        "optional_clue_ids": ["clue_moonlit_night"],
        "story_purpose": {
            "summary": "생물 반응을 통해 앞선 빛과 가루 단서를 보강한다.",
            "player_goal": "색 변화가 어디에서 더 강하게 나타나는지 확인한다.",
            "emotional_tone": "귀여운 생물 관찰에서 시작하는 조용한 긴장감.",
        },
        "steps": [
            ("observe_field", "관찰", "말랑 들판의 방울젤리 색을 확인한다.", "patrol_leader_rio", "soft_field", "평소보다 진한 색을 띠는 개체가 보인다.", "가까이 가되 방심하지 마라.", ["clue_jelly_color_change"], "색 변화 확인"),
            ("compare_area", "힌트", "숲 입구와 가까운 곳의 변화를 비교한다.", "mage_lumi", "soft_field", "숲 입구 가까운 곳에서 변화가 더 잦다.", "위치 차이를 봐야 해.", [], "위치 비교"),
            ("test_reaction", "단서", "마법 잡화점에서 약한 반응을 확인한다.", "mage_lumi", "magic_shop", "루미의 도구가 약한 반응을 보인다.", "결정적 답은 아니지만 흐름은 있어.", ["clue_mana_reaction"], "반응 확인"),
            ("report_pattern", "추론", "로완에게 빛과 색 변화의 공통점을 보고한다.", "chief_rowan", "hazel_square", "로완은 같은 시기와 방향을 비교하게 한다.", "같은 방향을 가리키는지 살펴보게.", [], "종합 후보 확보"),
        ],
        "wrong_hypotheses": [
            {
                "hypothesis_id": "jelly_seasonal_color",
                "text": "방울젤리의 계절성 색 변화다.",
                "why_it_seems_possible": "생물은 계절과 환경에 따라 달라질 수 있다.",
                "disproof_clue_ids": ["clue_mana_reaction"],
                "npc_reaction": "루미는 위치와 반응이 일정하게 겹친다고 설명한다.",
            }
        ],
        "hint_flow": {
            "hint_0": "색이 다른 개체만 보지 말고 위치를 비교한다.",
            "hint_1": "숲 입구와 가까울수록 변화가 잦은지 확인한다.",
            "hint_2": "마법적 반응을 별도로 확인한다.",
            "final_hint": "빛, 색, 반응이 같은 흐름에 놓일 수 있다.",
        },
    },
    "q_changed_signpost": {
        "episode_order": 4,
        "quest_role": "misdirection_check",
        "type": "investigation_quiz",
        "summary": "반복적으로 바뀐 표지판을 장난으로 단정하지 않고, 사람 발자국이 없는 현장과 뿌리 자국을 확인한다.",
        "main_location_ids": ["whispering_forest_entrance", "training_ground", "hazel_square"],
        "optional_clue_ids": ["clue_glittering_powder"],
        "story_purpose": {
            "summary": "플레이어가 보기 쉬운 용의자를 만들기보다 물리적 반증을 따라가게 한다.",
            "player_goal": "표지판 변경의 실제 단서를 현장에서 확인한다.",
            "emotional_tone": "장난처럼 보이는 사건이 다른 변화와 이어지는 느낌.",
        },
        "steps": [
            ("inspect_sign", "관찰", "숲 입구 표지판이 바뀐 상태를 본다.", "patrol_leader_rio", "whispering_forest_entrance", "표지판 방향이 평소와 다르다.", "표지판만 보지 말고 주변을 봐라.", ["clue_changed_signpost"], "표지판 확인"),
            ("search_ground", "힌트", "표지판 주변 발자국을 찾는다.", "patrol_leader_rio", "whispering_forest_entrance", "사람 발자국 대신 뿌리 자국과 나뭇조각이 보인다.", "사람이 한 흔적은 아니다.", ["clue_root_marks"], "뿌리 자국 확인"),
            ("ask_rumor", "단서", "민민 부인에게 숲속 생물 소문을 묻는다.", "minmin_lady", "east_farm", "장난기 많은 숲속 생물 이야기를 듣지만 확정하지 않는다.", "소문은 소문일 뿐이란다.", [], "소문과 증거 분리"),
            ("connect_spore", "추론", "루미에게 생물 반응 가능성을 묻는다.", "mage_lumi", "magic_shop", "포자 주변에서 생물이 민감해질 수 있다는 가능성을 듣는다.", "가능성은 있지만 현장 단서가 먼저야.", [], "다음 종합으로 연결"),
        ],
        "wrong_hypotheses": [
            {
                "hypothesis_id": "children_prank",
                "text": "아이들이 장난으로 표지판을 돌렸다.",
                "why_it_seems_possible": "마을 안의 작은 장난처럼 보인다.",
                "disproof_clue_ids": ["clue_root_marks"],
                "npc_reaction": "리오는 사람 발자국이 없다는 점을 강조한다.",
            }
        ],
        "hint_flow": {
            "hint_0": "표지판 방향만 보지 않는다.",
            "hint_1": "발자국과 주변 파편을 확인한다.",
            "hint_2": "소문과 물리 증거를 구분한다.",
            "final_hint": "사람 장난이 아니라 숲 방향의 변화와 연결해 본다.",
        },
    },
    "q_main_spore_night": {
        "episode_order": 5,
        "quest_role": "final_synthesis",
        "type": "main_inference",
        "summary": "앞선 네 사건의 빛, 발자국, 색 변화, 표지판 단서를 종합해 하나의 흐름을 추론하는 최종 정리 퀘스트.",
        "main_location_ids": ["hazel_square", "whispering_forest_entrance", "magic_shop", "moonlight_spring"],
        "optional_clue_ids": ["clue_mana_reaction", "clue_root_marks"],
        "story_purpose": {
            "summary": "각 NPC가 가진 부분 지식을 한 번에 합쳐도, 단서 조건 전에는 정답을 직접 주지 않게 한다.",
            "player_goal": "네 가지 작은 사건이 같은 방향과 조건을 가리키는지 정리한다.",
            "emotional_tone": "작은 관찰들이 하나의 그림으로 맞물리는 조용한 해결감.",
        },
        "steps": [
            ("gather_reports", "관찰", "민민, 리오, 루미의 보고를 정리한다.", "chief_rowan", "hazel_square", "생활 관찰, 물리 증거, 마법 가설을 한자리에 둔다.", "각자 본 것이 다르다는 점을 잊지 말게.", [], "보고 수집"),
            ("align_direction", "힌트", "사건들이 어느 방향을 가리키는지 비교한다.", "patrol_leader_rio", "hazel_square", "발자국과 표지판 사건이 숲 입구를 가리킨다.", "방향이 반복된다.", ["clue_pig_tracks", "clue_changed_signpost"], "방향성 확인"),
            ("align_reaction", "단서", "빛과 색 변화, 반응 흔적을 비교한다.", "mage_lumi", "magic_shop", "버섯, 방울젤리, 가루가 같은 흐름 후보가 된다.", "셋을 따로 보지 마.", ["clue_bright_mushroom", "clue_jelly_color_change", "clue_mana_reaction"], "반응성 확인"),
            ("test_answer", "추론", "필요 단서가 모였는지 확인하고 답을 말한다.", "chief_rowan", "hazel_square", "로완은 플레이어의 추론이 단서와 맞는지 검토한다.", "단서가 모였다면 이제 말해 보게.", [], "필수 단서 충족"),
            ("close_case", "완료", "사건 후 NPC들의 역할을 정리한다.", "chief_rowan", "hazel_square", "각 NPC가 아는 범위를 지킨 채 해결 후 반응을 말한다.", "정답보다 중요한 것은 관찰을 잇는 법일세.", [], "완료"),
        ],
        "wrong_hypotheses": [
            {
                "hypothesis_id": "single_culprit_only",
                "text": "한 명의 장난이나 한 사건만으로 모든 일이 벌어졌다.",
                "why_it_seems_possible": "표지판 사건만 보면 장난처럼 보인다.",
                "disproof_clue_ids": ["clue_bright_mushroom", "clue_pig_tracks", "clue_jelly_color_change"],
                "npc_reaction": "로완은 서로 다른 증거가 같은 시기와 방향에 모인다고 정리한다.",
            },
            {
                "hypothesis_id": "pure_magic_only",
                "text": "마법 현상 하나가 모든 행동을 직접 지배했다.",
                "why_it_seems_possible": "빛과 반응 흔적이 강하게 보인다.",
                "disproof_clue_ids": ["clue_pig_tracks", "clue_root_marks"],
                "npc_reaction": "리오는 실제 움직임과 흔적을 빼면 설명이 불완전하다고 말한다.",
            },
        ],
        "hint_flow": {
            "hint_0": "네 사건을 따로 보지 않는다.",
            "hint_1": "방향과 시간 조건을 비교한다.",
            "hint_2": "생물 반응과 물리 흔적을 함께 본다.",
            "final_hint": "필수 단서가 모였을 때만 최종 추론을 말한다.",
        },
    },
}


def ensure_dirs() -> None:
    for path in [REPORTS_DIR, INTEGRATED_DIR, NEO4J_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML mapping expected: {path}")
    return data


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValueError(f"Missing YAML frontmatter: {path}")
    frontmatter = yaml.safe_load(match.group(1)) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError(f"Frontmatter mapping expected: {path}")
    return frontmatter, text[match.end() :]


def read_sources() -> dict[str, Any]:
    npcs: dict[str, dict[str, Any]] = {}
    chunk_counts: dict[str, int] = {}
    for path in sorted((SOURCE_DIR / "npcs").glob("*.md")):
        frontmatter, body = parse_frontmatter(path)
        npc_id = str(frontmatter["npc_id"])
        npcs[npc_id] = {"frontmatter": frontmatter, "body": body, "source_file": path.relative_to(ROOT).as_posix()}
        chunk_counts[npc_id] = body.count("```chunk") + body.count("```story-chunk")

    quests: dict[str, dict[str, Any]] = {}
    for path in sorted((SOURCE_DIR / "quests").glob("*.yaml")):
        quest = load_yaml(path)
        quests[str(quest["quest_id"])] = {**quest, "source_file": path.relative_to(ROOT).as_posix()}

    locations: dict[str, dict[str, Any]] = {}
    for path in sorted((SOURCE_DIR / "locations").glob("*.md")):
        frontmatter, body = parse_frontmatter(path)
        location_id = str(frontmatter["location_id"])
        summary = str(frontmatter.get("summary") or body.strip().split("\n\n")[0].strip())
        locations[location_id] = {**frontmatter, "id": location_id, "summary": summary, "source_file": path.relative_to(ROOT).as_posix()}

    clues_data = load_yaml(SOURCE_DIR / "world" / "clues.yaml")
    truths_data = load_yaml(SOURCE_DIR / "world" / "truths.yaml")
    events_data = load_yaml(SOURCE_DIR / "world" / "events.yaml")
    roles_data = load_yaml(SOURCE_DIR / "world" / "roles.yaml")
    policies_data = load_yaml(SOURCE_DIR / "world" / "dialogue_policies.yaml")

    return {
        "npcs": npcs,
        "chunk_counts": chunk_counts,
        "quests": quests,
        "locations": locations,
        "clues": clues_data.get("clues", []),
        "truths": truths_data.get("truths", []),
        "events": events_data.get("events", []),
        "roles": roles_data.get("roles", []),
        "knowledge_types": roles_data.get("knowledge_types", []),
        "dialogue_policies": policies_data,
    }


def unknown_truth_ids_for(npc_id: str) -> list[str]:
    if npc_id == "chief_rowan":
        return []
    if npc_id == "mage_lumi":
        return ["truth_spore_scent_attraction", "truth_stump_followed_spores"]
    if npc_id == "patrol_leader_rio":
        return ["truth_moonwell_mana_cycle", "truth_spore_scent_attraction", "truth_stump_followed_spores"]
    return ["truth_moonwell_mana_cycle", "truth_spore_scent_attraction", "truth_stump_followed_spores"]


def forbidden_truth_ids_for(npc_id: str) -> list[str]:
    if npc_id == "chief_rowan":
        return []
    return TRUTH_IDS.copy()


def pre_reveal_forbidden_truth_ids() -> list[str]:
    return TRUTH_IDS.copy()


def make_dialogues() -> list[dict[str, Any]]:
    templates: dict[str, list[tuple[str, str, str, str, list[str], str]]] = {
        "minmin_lady": [
            ("first_01", "first_meet", "처음 왔어요. 어디부터 보면 될까요?", "아이고, 신발부터 털고 가렴. 처음 온 모험가는 광장 길과 농장 울타리부터 익히는 게 좋단다. 작은 생물도 놀라면 제법 빠르니 밥 먹고 천천히 보렴.", [], "q_glowing_mushroom"),
            ("first_02", "first_meet", "숲에 바로 가도 될까요?", "밥도 안 먹고 숲부터 가면 걱정되잖니. 낮에 길 모양, 표지판, 돌아오는 길을 먼저 봐 두렴. 밤에는 같은 길도 전혀 다르게 보인단다.", [], "q_glowing_mushroom"),
            ("chat_01", "small_talk", "농장은 늘 이렇게 바쁜가요?", "농장은 조용해 보여도 매일 다른 얼굴이란다. 흙냄새, 울타리 긁힌 자국, 말랑돼지 콧소리만 들어도 어제와 오늘이 조금씩 다르지 뭐니.", [], "q_pig_escape"),
            ("chat_02", "small_talk", "말랑돼지는 순한가요?", "순하지. 그래도 겁이 많고 냄새에 예민해서 낯선 자극을 맡으면 한쪽으로 몰리곤 한단다. 그러니 발자국 방향을 그냥 지나치면 안 돼.", ["clue_pig_tracks"], "q_pig_escape"),
            ("hint_01", "quest_hint", "몽실버섯이 왜 빛나요?", "왜인지는 몰라도, 달이 밝던 밤에 유난히 눈에 띄었단다. 낮에는 얌전했는데 밤에는 작은 등불처럼 보였으니 시간과 달빛을 나누어 보렴.", ["clue_moonlit_night"], "q_glowing_mushroom"),
            ("hint_02", "quest_hint", "말랑돼지가 왜 나갔죠?", "먹이는 충분했단다. 배고파서 나간 거라면 먹이통부터 비었겠지. 이번에는 냄새, 발자국, 숲 쪽 방향을 차례로 살펴야 하지 않겠니.", ["clue_pig_tracks"], "q_pig_escape"),
            ("hint_03", "quest_hint", "들판 생물이 이상해요.", "방울젤리 색이 달라 보였다는 말은 나도 들었단다. 나는 생활 변화만 느낄 뿐이니, 색과 반응은 루미에게 묻고 너는 위치를 잘 적어 두렴.", ["clue_jelly_color_change"], "q_jelly_color"),
            ("avoid_01", "answer_probe", "정답을 바로 말해 주세요.", "내가 본 건 빛과 냄새와 움직임뿐이란다. 큰 원인은 네가 단서를 모아 생각해야지. 밥도 뜸이 들어야 맛나듯 추리도 순서가 필요하단다.", [], "q_main_spore_night"),
            ("avoid_02", "answer_probe", "범인이 누구예요?", "그런 말은 함부로 하면 안 된단다. 소문만 듣고 누굴 찍으면 농사도 추리도 망치는 법이야. 표지판 주변에 남은 걸 먼저 보렴.", [], "q_changed_signpost"),
            ("after_01", "after_solved", "이제 괜찮을까요?", "한시름 놓았구나. 그래도 밭과 숲길은 천천히 살펴야 한단다. 오늘 배운 건 정답 하나가 아니라 작은 변화를 놓치지 않는 습관이니까.", [], "q_main_spore_night"),
        ],
        "patrol_leader_rio": [
            ("first_01", "first_meet", "순찰에 따라가도 됩니까?", "따라와도 좋다. 단, 지시 없이 숲에 들어가지 마라. 귀여운 생물과 낮은 울타리만 보여도 현장은 현장이다. 먼저 발밑과 퇴로를 확인해라.", [], "q_pig_escape"),
            ("first_02", "first_meet", "위험한 곳이 있나요?", "위험은 방심하는 곳에서 생긴다. 말랑 들판처럼 평범한 장소도 색, 움직임, 발자국이 달라지면 조사 대상이다. 들판부터 제대로 확인해라.", [], "q_jelly_color"),
            ("chat_01", "small_talk", "왜 그렇게 기록을 많이 하나요?", "기록은 기억보다 정확하다. 오늘 본 흙자국이 내일 같은 방향으로 반복되면 소문이 아니라 사건이 된다. 그래서 나는 짧게라도 반드시 적는다.", [], "q_changed_signpost"),
            ("chat_02", "small_talk", "훈련장은 무섭네요.", "무서워도 다치는 것보다 낫다. 기본 자세, 거리, 시야만 지켜도 초보자가 피할 사고는 많다. 겁은 숨기지 말고 규칙으로 다뤄라.", [], "q_pig_escape"),
            ("hint_01", "quest_hint", "말랑돼지는 어디로 갔죠?", "발자국은 흩어지지 않았다. 같은 간격으로 숲 입구 방향을 향했다. 무작정 도망친 흔적이 아니니 먹이 문제만 보고 판단하지 마라.", ["clue_pig_tracks"], "q_pig_escape"),
            ("hint_02", "quest_hint", "표지판은 누가 바꿨죠?", "사람 발자국은 없었다. 대신 뿌리처럼 끌린 자국과 작은 나뭇조각이 있었다. 누가 했는지보다 어떤 흔적이 남았는지를 먼저 봐라.", ["clue_root_marks"], "q_changed_signpost"),
            ("hint_03", "quest_hint", "반짝이는 가루가 중요합니까?", "정체는 모른다. 하지만 발자국 옆, 울타리 바깥, 숲 방향에서 같이 보였다. 모르는 물건일수록 이름보다 위치와 반복성을 기록해야 한다.", ["clue_glittering_powder"], "q_pig_escape"),
            ("avoid_01", "answer_probe", "마법 때문인가요?", "나는 마법을 판단하지 않는다. 내가 말할 수 있는 건 파손, 발자국, 방향, 현장 기록뿐이다. 원리 설명은 루미에게 듣고, 결론은 증거를 모은 뒤 말해라.", [], "q_main_spore_night"),
            ("avoid_02", "answer_probe", "결론을 알려 주세요.", "결론은 증거를 모은 뒤에 말해라. 지금은 현장을 더 봐야 한다. 빠진 단서가 있으면 맞는 말도 추측이 되고, 추측은 순찰 기록에 쓰지 않는다.", [], "q_main_spore_night"),
            ("after_01", "after_solved", "수고하셨습니다.", "잘했다. 다음에도 귀여운 몬스터라고 방심하지 마라. 약한 생물도 습성이 있고, 습성이 반복되면 단서가 된다. 그걸 기억해라.", [], "q_main_spore_night"),
        ],
        "mage_lumi": [
            ("first_01", "first_meet", "여기가 마법 잡화점인가요?", "맞아, 그리고 작은 실험실이기도 해. 반짝이는 병과 꿈틀거리는 표본은 만지기 전에 꼭 물어봐 줘. 귀여운 재료일수록 갑자기 튀는 법이거든.", [], "q_glowing_mushroom"),
            ("first_02", "first_meet", "무엇을 연구하세요?", "마을 주변의 작은 반응들 말이야. 버섯의 빛, 방울젤리의 색, 울타리 근처 가루처럼 사소해 보이는 현상이 서로 말을 걸 때가 있거든.", [], "q_jelly_color"),
            ("chat_01", "small_talk", "실험은 자주 실패하나요?", "실패도 기록하면 자료야. 폭발만 안 하면 꽤 훌륭하지. 실패한 병 색, 냄새, 시간까지 적어 두면 다음 가설이 훨씬 덜 엉망이 돼.", [], "q_jelly_color"),
            ("chat_02", "small_talk", "방울젤리를 좋아하나요?", "좋아하지. 방울젤리는 주변 흐름을 솔직하게 보여 주는 편이야. 색이 달라졌다면 겁내기보다 위치와 시간을 비교해 보는 게 먼저야.", ["clue_jelly_color_change"], "q_jelly_color"),
            ("hint_01", "quest_hint", "버섯 빛이 이상해요.", "빛만 보지 말고 조건을 봐. 달, 시간, 주변 가루가 같이 움직이는지 말이야. 하나는 신기한 장면이고, 셋이 겹치면 조사할 만한 반응이 돼.", ["clue_bright_mushroom", "clue_moonlit_night"], "q_glowing_mushroom"),
            ("hint_02", "quest_hint", "가루가 뭔가요?", "포자일 가능성은 있어. 하지만 가능성과 결론은 다르니까 더 확인하자. 냄새나 빛, 생물 움직임과 함께 나타났는지가 더 중요해.", ["clue_glittering_powder"], "q_pig_escape"),
            ("hint_03", "quest_hint", "젤리 색은 왜 변했죠?", "주변 흐름에 민감한 생물이라면 작은 변화도 색으로 보일 수 있어. 다만 어디서 더 진해지는지, 내 도구가 어떤 반응을 보이는지 같이 봐야 해.", ["clue_jelly_color_change", "clue_mana_reaction"], "q_jelly_color"),
            ("avoid_01", "answer_probe", "모든 원인을 알죠?", "아직은 가설이야. 민민 부인의 생활 관찰과 리오의 현장 기록 없이 단정하면 실험도 추리도 망가져. 나는 연결 가능성을 말할 뿐이야.", [], "q_main_spore_night"),
            ("avoid_02", "answer_probe", "표지판 사건도 설명해 주세요.", "가능성은 말할 수 있지만, 현장 흔적은 리오가 더 정확해. 나는 생물이 자극에 반응했을 수도 있다고만 말할게. 확정은 단서가 더 필요해.", [], "q_changed_signpost"),
            ("after_01", "after_solved", "분석이 맞았네요.", "가설이 단서와 맞아떨어진 거지. 다음엔 기록부터 더 깔끔하게 해 보자. 빛, 냄새, 색, 위치를 같이 적으면 작은 사건도 훨씬 잘 보이거든.", [], "q_main_spore_night"),
        ],
        "chief_rowan": [
            ("first_01", "first_meet", "촌장님을 뵈러 왔습니다.", "잘 왔네. 이 마을에서는 작은 변화도 놓치지 않는 눈이 필요하다네. 평화로운 광장도 주민의 보고가 쌓이면 하나의 기록이 되지.", [], "q_main_spore_night"),
            ("first_02", "first_meet", "무슨 일이 있나요?", "몇 가지 보고가 들어왔네. 먼저 사람들이 직접 본 것을 들어 보게. 누가 보았는지, 어디서 보았는지, 무엇을 추측했는지를 나누어야 하네.", [], "q_glowing_mushroom"),
            ("chat_01", "small_talk", "광장은 평화로워 보입니다.", "평화로워 보이는 곳일수록 작은 불안을 빨리 알아차려야 하네. 큰 소동이 되기 전의 기록은 대개 아주 사소한 말에서 시작되네.", [], "q_main_spore_night"),
            ("chat_02", "small_talk", "기록을 많이 보시나요?", "기록은 답을 대신 주지 않지만, 질문의 순서를 알려 주곤 하지. 어느 장을 먼저 읽어야 하는지 알면 결론을 서두르지 않게 되네.", [], "q_main_spore_night"),
            ("hint_01", "quest_hint", "누구에게 먼저 가야 하나요?", "농장의 변화는 민민 부인에게, 흔적은 리오에게, 반응은 루미에게 묻게. 각자 아는 범위가 다르니 한 사람의 말만으로 결론을 내리지 말게.", [], "q_main_spore_night"),
            ("hint_02", "quest_hint", "단서가 흩어져 있습니다.", "흩어진 것이 아니라 각자 다른 자리에서 같은 방향을 말하는지 보게. 시간, 위치, 생물의 움직임을 나란히 놓으면 빈칸이 보일 걸세.", [], "q_main_spore_night"),
            ("hint_03", "quest_hint", "어떤 단서가 중요합니까?", "빛, 발자국, 색 변화, 표지판 흔적을 따로 두지 말고 함께 놓아 보게. 직접 본 사실과 가설을 구분하면 자네의 추론이 훨씬 단단해질 걸세.", ["clue_bright_mushroom", "clue_pig_tracks", "clue_jelly_color_change", "clue_changed_signpost"], "q_main_spore_night"),
            ("avoid_01", "answer_probe", "촌장님은 알고 계시죠?", "알고 있는 것과 지금 말해야 하는 것은 다르다네. 내가 먼저 말하면 자네는 단서를 잇는 법을 놓칠 수 있네. 자네의 추론을 먼저 듣고 싶네.", [], "q_main_spore_night"),
            ("avoid_02", "answer_probe", "정답만 알려 주세요.", "정답만 들으면 다음 변화는 보지 못하네. 필수 단서가 모였는지, 각 단서가 어떤 순서로 이어지는지 먼저 확인하게. 그다음에 판단해도 늦지 않네.", [], "q_main_spore_night"),
            ("after_01", "after_solved", "마을이 안정될까요?", "오늘은 그렇네. 하지만 자네가 배운 관찰법은 앞으로도 필요할 걸세. 이 마을은 크게 변하지 않아도 작은 기록은 계속 쌓일 테니까.", [], "q_main_spore_night"),
        ],
    }
    dialogues: list[dict[str, Any]] = []
    for npc_id, rows in templates.items():
        for suffix, condition, player, npc, clues, quest_id in rows:
            dialogues.append(
                {
                    "id": f"dlg_{npc_id}_{suffix}",
                    "npc_id": npc_id,
                    "quest_id": quest_id,
                    "condition": condition,
                    "player_text": player,
                    "npc_text": npc,
                    "allowed_clue_ids": clues,
                    "forbidden_truth_ids": pre_reveal_forbidden_truth_ids(),
                    "related_quest_id": quest_id,
                    "note": "단서 조건 전에는 최종 진실을 직접 말하지 않는 예시.",
                    "source_file": f"rsc/data/npcs/{npc_id}.md",
                }
            )
    return dialogues


def npc_markdown(npc_id: str, source: dict[str, Any], expansion: dict[str, Any], dialogues: list[dict[str, Any]]) -> str:
    relationships = expansion["relationships"]
    quest_roles = expansion["quest_roles"]
    known_notes = expansion["known_clue_notes"]
    lines = [f"# {expansion['display_name']}", "", "## 1. 인물 개요", "", *expansion["overview"], "", "## 2. 현재 역할", "", expansion["current_role"], "", "## 3. 성격과 말투", ""]
    speech = expansion["speech_style"]
    lines.extend([f"- 문장 길이: {speech['sentence_length']}", f"- 어휘 특징: {speech['vocabulary']}", f"- 플레이어를 부르는 방식: {speech['player_address']}", f"- 감정 표현 방식: {speech['emotion']}", f"- 절대 하지 않는 말투: {speech['never']}", "", "## 4. 과거 배경", "", *expansion["background"], "", "## 5. 하루 루틴", ""])
    for key, label in [("morning", "아침"), ("day", "낮"), ("evening", "저녁"), ("night", "밤")]:
        lines.append(f"- {label}: {expansion['routine'][key]}")
    lines.extend(["", "## 6. 다른 등장인물과의 관계", ""])
    for other_id, text in relationships.items():
        lines.append(f"- {other_id}: {text}")
    lines.extend(["", "## 7. 퀘스트별 관여 방식", ""])
    for quest_id in QUEST_ORDER:
        lines.append(f"- {quest_id}: {quest_roles[quest_id]}")
    lines.extend(["", "## 8. 알고 있는 단서", ""])
    for clue_id in expansion["known_clue_ids"]:
        lines.append(f"- {clue_id}: {known_notes[clue_id]}")
    lines.extend(["", "## 9. 모르는 진실", ""])
    unknown = unknown_truth_ids_for(npc_id)
    if unknown:
        for truth_id in unknown:
            lines.append(f"- {truth_id}: 직접 관찰하거나 검증한 정보가 아니므로 단정해서 말하지 않는다.")
    else:
        lines.append("- 없음: 다만 필수 단서가 모이기 전에는 어떤 truth_id도 직접 공개하지 않는다.")
    lines.extend(["", "## 10. 신뢰도 단계별 반응", "", "- trust_0: 처음 만남. 자기 역할과 안전한 조사 순서만 알려 주고 깊은 결론은 숨긴다.", "- trust_1: 단서를 1개 이상 확인한 상태. 자신이 직접 아는 clue_id 범위에서 힌트를 더 구체화한다.", "- trust_2: 퀘스트 후반 또는 도움을 준 상태. 다른 NPC의 증거와 연결하라고 권하지만 forbidden_truth_ids는 직접 말하지 않는다.", "", "## 11. 대화 예시", ""])
    for dialogue in dialogues:
        if dialogue["npc_id"] != npc_id:
            continue
        lines.extend(
            [
                f"### {dialogue['id']}",
                "",
                f"* condition: {dialogue['condition']}",
                f"* player: {dialogue['player_text']}",
                f"* npc: {dialogue['npc_text']}",
                f"* allowed_clue_ids: {dialogue['allowed_clue_ids']}",
                f"* forbidden_truth_ids: {dialogue['forbidden_truth_ids']}",
                f"* related_quest_id: {dialogue['related_quest_id']}",
                f"* note: {dialogue['note']}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def quest_data(quest_id: str, original: dict[str, Any]) -> dict[str, Any]:
    expansion = original.get("story_expansion") or QUEST_EXPANSIONS[quest_id]
    if "quest_steps" in expansion:
        steps = list(expansion["quest_steps"])
    else:
        steps = [
            {
                "step_id": row[0],
                "title": row[1],
                "objective": row[2],
                "npc_id": row[3],
                "location_id": row[4],
                "player_observation": row[5],
                "npc_hint": row[6],
                "unlocked_clue_ids": row[7],
                "next_step_condition": row[8],
            }
            for row in expansion["steps"]
        ]
    involved = list(original.get("involved_npc_ids", []))
    required = list(original.get("required_clue_ids", []))
    answer_truths = list(original.get("answer_truth_ids", []))
    return {
        "id": quest_id,
        "quest_id": quest_id,
        "title": original["title"],
        "episode_order": expansion["episode_order"],
        "quest_role": expansion["quest_role"],
        "type": expansion["type"],
        "summary": expansion["summary"],
        "involved_npc_ids": involved,
        "main_location_ids": expansion["main_location_ids"],
        "required_clue_ids": required,
        "optional_clue_ids": expansion["optional_clue_ids"],
        "answer_truth_ids": answer_truths,
        "story_purpose": expansion["story_purpose"],
        "quest_steps": steps,
        "wrong_hypotheses": expansion["wrong_hypotheses"],
        "hint_flow": expansion["hint_flow"],
        "answer_reveal_policy": {
            "can_reveal_truth_before_required_clues": False,
            "required_before_reveal": required,
            "npc_allowed_to_reveal": ["chief_rowan"],
            "npc_not_allowed_to_reveal": [npc_id for npc_id in NPC_ORDER if npc_id != "chief_rowan"],
        },
        "completion": {
            "player_answer_condition": "required_clue_ids가 모두 확인되고 플레이어가 단서 연결을 말한다.",
            "success_dialogue": "단서가 충분히 모였을 때만 NPC가 추론을 인정한다.",
            "partial_success_dialogue": "방향은 맞지만 빠진 단서를 다시 확인하게 한다.",
            "after_effect": "마을은 즉시 크게 변하지 않지만 NPC별 후속 대사가 열린다.",
        },
        "source_file": original["source_file"],
        "original_fields": original,
    }


def build_integrated_data(sources: dict[str, Any], dialogues: list[dict[str, Any]]) -> dict[str, Any]:
    npcs = []
    for npc_id in NPC_ORDER:
        original = sources["npcs"][npc_id]["frontmatter"]
        expansion = NPC_EXPANSIONS[npc_id]
        npcs.append(
            {
                "id": npc_id,
                "name": original["name"],
                "role": original["role"],
                "location_id": original["location_id"],
                "main_quest": original.get("main_quest"),
                "personality_summary": expansion["personality_summary"],
                "speech_style": expansion["speech_style_summary"],
                "known_clue_ids": expansion["known_clue_ids"],
                "unknown_truth_ids": unknown_truth_ids_for(npc_id),
                "forbidden_truth_ids": forbidden_truth_ids_for(npc_id),
                "source_file": sources["npcs"][npc_id]["source_file"],
                "original_fields": original,
                "expanded_fields": {
                    "overview": expansion["overview"],
                    "current_role": expansion["current_role"],
                    "routine": expansion["routine"],
                    "relationships": expansion["relationships"],
                    "quest_roles": expansion["quest_roles"],
                    "known_clue_notes": expansion["known_clue_notes"],
                },
            }
        )

    quests = [quest_data(quest_id, sources["quests"][quest_id]) for quest_id in QUEST_ORDER]
    clues = [
        {
            "id": clue["clue_id"],
            "title": clue["name"],
            "text": clue["name"],
            "hint_level": clue.get("hint_level", 0),
            "is_optional": False,
            "source_file": "rsc/data/world/clues.yaml",
            "original_fields": clue,
        }
        for clue in sources["clues"]
    ]
    truths = [
        {
            "id": truth["truth_id"],
            "title": truth["name"],
            "summary": truth["name"],
            "answer_sensitive": truth.get("answer_sensitive", True),
            "source_file": "rsc/data/world/truths.yaml",
            "original_fields": truth,
        }
        for truth in sources["truths"]
    ]
    locations = [
        {
            "id": location_id,
            "name": location["name"],
            "summary": location["summary"],
            "source_file": location["source_file"],
            "original_fields": location,
        }
        for location_id, location in sorted(sources["locations"].items())
    ]
    return {
        "metadata": {
            "title": "Hazel Village NPC Persona Expansion",
            "generated_by": "scripts/story_pipeline/build_integrated_data.py",
            "scope": "4 NPCs, 5 quests, existing clues/truths/locations, dialogue examples only",
            "source_dir": "rsc/data",
        },
        "new_major_regions": [],
        "new_npcs": [],
        "npcs": npcs,
        "quests": quests,
        "clues": clues,
        "truths": truths,
        "locations": locations,
        "dialogues": dialogues,
        "dialogue_policies": sources["dialogue_policies"],
    }


def write_yaml(path: Path, data: Any) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_story_reports(sources: dict[str, Any], data: dict[str, Any]) -> None:
    dialogues = data["dialogues"]
    overview = [
        "# 헤이즐 마을 퀘스트 라인 개요",
        "",
        "## 전체 퀘스트 라인 요약",
        "",
        "다섯 퀘스트는 MapleStory Grand Athenaeum/Dimensional Library의 '이야기 보관소에서 에피소드를 따라가며 재확인하는 구조'를 참고하되, 보강 자료는 별도 생성 폴더가 아니라 기존 rsc/data/quests/*.yaml의 story_expansion에 통합한다.",
        "플레이어는 빛, 발자국, 색 변화, 표지판 흔적을 차례로 모으고 q_main_spore_night에서 종합한다.",
        "",
        "## 각 퀘스트의 역할",
    ]
    for quest in data["quests"]:
        overview.append(f"- {quest['id']}: {quest['quest_role']} / {quest['summary']}")
    overview.extend([
        "",
        "## 앞 퀘스트의 단서 연결",
        "",
        "q_glowing_mushroom은 빛과 달빛 조건을 열고, q_pig_escape는 숲 방향의 물리 흔적을 더한다.",
        "q_jelly_color는 생물 반응을 통해 환경 신호를 보강하고, q_changed_signpost는 장난처럼 보이는 사건을 물리 증거로 반박한다.",
        "",
        "## q_main_spore_night에서 종합되는 단서",
        "",
        "강한 버섯빛, 달 밝은 밤, 숲 방향 발자국, 반짝이는 가루, 방울젤리 색 변화, 바뀐 표지판, 뿌리 자국, 마나 반응 흔적을 운영자가 조합한다.",
        "",
        "## 스포일러 없는 플레이어용 요약",
        "",
        "작은 마을에서 벌어진 귀여운 이상 현상들을 각 NPC의 관점으로 조사한다.",
        "",
        "## 스포일러 포함 운영자용 요약",
        "",
        "각 사건은 단일 범인 찾기가 아니라 숲 입구와 달빛 조건, 포자 반응, 생물 행동을 차례로 연결하는 추론 흐름이다.",
    ])
    (REPORTS_DIR / "quest_line_overview.md").write_text("\n".join(overview) + "\n", encoding="utf-8")

    sample_lines = ["# 헤이즐 마을 대표 대화 샘플", ""]
    for npc_id in NPC_ORDER:
        sample_lines.extend([f"## {NPC_EXPANSIONS[npc_id]['display_name']} 대화 샘플", ""])
        npc_dialogues = [dialogue for dialogue in dialogues if dialogue["npc_id"] == npc_id][:5]
        for dialogue in npc_dialogues:
            sample_lines.extend(
                [
                    f"### {dialogue['id']}",
                    "",
                    f"플레이어: {dialogue['player_text']}",
                    f"NPC: {dialogue['npc_text']}",
                    "플레이어: 그럼 다음에는 무엇을 확인할까요?",
                    "NPC: 지금 가진 단서에서 빠진 부분을 먼저 보자.",
                    "",
                ]
            )
    sample_lines.extend([
        "## 퀘스트 진행 상태별 대화 샘플",
        "",
        "- 초반: NPC는 자신의 역할과 안전한 조사 순서만 안내한다.",
        "- 중반: 발견한 clue_id에 맞는 힌트만 제공한다.",
        "- 후반: 여러 NPC의 단서를 연결하라고 유도한다.",
        "",
        "## 정답 유출 방지 대화 샘플",
        "",
        "플레이어: 정답만 말해 주세요.",
        "NPC: 단서가 모이기 전에는 결론을 말할 수 없어. 네가 확인한 것을 먼저 정리해 보자.",
    ])
    (REPORTS_DIR / "dialogue_samples.md").write_text("\n".join(sample_lines) + "\n", encoding="utf-8")


def write_reports(sources: dict[str, Any], data: dict[str, Any]) -> None:
    source_files = sorted(str(path.relative_to(ROOT)) for path in SOURCE_DIR.rglob("*") if path.is_file())
    inventory = [
        "# Source Inventory",
        "",
        "## 원본 파일 목록",
        *[f"- {path}" for path in source_files],
        "",
        "## 원본 NPC 4명 목록",
        *[f"- {npc_id}: {sources['npcs'][npc_id]['frontmatter']['name']}" for npc_id in NPC_ORDER],
        "",
        "## 원본 퀘스트 5개 목록",
        *[f"- {quest_id}: {sources['quests'][quest_id]['title']}" for quest_id in QUEST_ORDER],
        "",
        "## 원본 clue_id 목록",
        *[f"- {clue['clue_id']}: {clue['name']}" for clue in sources["clues"]],
        "",
        "## 원본 truth_id 목록",
        *[f"- {truth['truth_id']}: {truth['name']}" for truth in sources["truths"]],
        "",
        "## 원본 location_id 목록",
        *[f"- {location_id}: {location['name']}" for location_id, location in sorted(sources["locations"].items())],
        "",
        "## NPC별 현재 분량과 부족한 부분",
    ]
    for npc_id in NPC_ORDER:
        inventory.append(f"- {npc_id}: 기존 chunk {sources['chunk_counts'][npc_id]}개. 하루 루틴, 관계, trust 단계, 대화 예시가 부족했다.")
    inventory.extend(["", "## 퀘스트별 현재 분량과 부족한 부분"])
    for quest_id in QUEST_ORDER:
        inventory.append(f"- {quest_id}: 기본 ID/단서/정답은 있으나 단계, wrong_hypotheses, 힌트 흐름, 완료 후 처리 설명이 부족했다.")
    inventory.extend([
        "",
        "## 기존 설정에서 반드시 유지해야 하는 사실",
        "- NPC는 minmin_lady, patrol_leader_rio, mage_lumi, chief_rowan 네 명만 사용한다.",
        "- 퀘스트는 기존 5개만 사용한다.",
        "- clue_id, truth_id, location_id는 기존 짧은 ID를 유지한다.",
        "- 정답 진실은 단서 조건 전까지 직접 공개하지 않는다.",
        "",
        "## 통합 시 충돌 가능성이 있는 부분",
        "- root raw Markdown은 작성 참고 자료이고 importer 직접 입력이 아니다.",
        "- 이번 Neo4j export schema는 output 전용이며 기존 MVP importer를 대체하지 않는다.",
        "- MapleStory 참고는 구조 참고용이며 원문 대사나 고유 스토리 문장은 복사하지 않는다.",
    ])
    (REPORTS_DIR / "source_inventory.md").write_text("\n".join(inventory) + "\n", encoding="utf-8")

    reference = """# Reference Research

확인 날짜: 2026-06-14

원문 대사나 고유 스토리 문장은 복사하지 않음. 아래 내용은 웹에서 확인한 구조와 운영 방식만 헤이즐 마을에 적용하기 위한 메모다.

## 1. MapleStory Grand Athenaeum / Dimensional Library

- 출처: MapleStory 공식 v.148 Grand Athenaeum Update Highlights, https://www.nexon.com/maplestory/news/2706/v-148-grand-athenaeum-update-highlights
- 출처: MapleStory Wiki Grand Athenaeum, https://maplestorywiki.net/w/Grand_Athenaeum (community source)
- 확인 구조: 도서관/기록 보관소를 허브로 두고, 플레이어가 독립된 에피소드로 진입한다.
- 헤이즐 반영: q_main_spore_night를 '기록을 정리하는 종합 에피소드'처럼 운영하고, 각 퀘스트는 작은 책/장처럼 구분한다.
- 주의: MapleStory 고유 인물, 대사, 사건 문장을 복제하지 않는다.

## 2. Grand Athenaeum 퀘스트 단계 구조

- 출처: MapleStory Wiki Grand Athenaeum Quests, https://maplestorywiki.net/w/Grand_Athenaeum_Quests (community source)
- 출처: Hidden Street Grand Athenaeum quest entry, https://www.hidden-street.net/gms/quest/grand-athenaeum-visit-the-grand-athenaeum (database source)
- 확인 구조: 요구 레벨, 입장/안내 NPC, 절차, 보상 같은 단계를 분리한다.
- 헤이즐 반영: 각 퀘스트를 관찰 -> 힌트 -> 단서 -> 추론 -> 완료 단계로 고정한다.
- 주의: 실제 MapleStory 절차 문장 대신 단계 구조만 사용한다.

## 3. Maple Chronicle / Story Replay 구조

- 출처: MapleStory Wiki Book of the Beginning, https://maplestorywiki.net/w/Book_of_the_Beginning (community source)
- 출처: Orange Mushroom KMST Dimensional Library: Maple Chronicles, https://orangemushroom.net/2022/10/20/kmst-ver-1-2-147-dimensional-library-maple-chronicles/ (patch translation/source commentary)
- 확인 구조: 완료한 이야기나 과거 모험을 챕터/책 형태로 다시 보기하고, 요약 보기/재입장 개념을 제공한다.
- 헤이즐 반영: rsc/data/quests/*.yaml의 story_expansion과 output/reports/quest_line_overview.md를 운영자용 story replay 인덱스로 두고, 해결 후 대화가 현재 상태를 바꾸지 않게 한다.
- 주의: 비공식/커뮤니티 자료는 구조 참고로만 사용한다.

## 4. Three Clue Rule

- 출처: The Alexandrian, Three Clue Rule, https://thealexandrian.net/wordpress/1118/roleplaying-games/three-clue-rule
- 확인 구조: 플레이어가 도달해야 하는 결론마다 최소 3개 단서 또는 대체 경로를 둔다.
- 헤이즐 반영: q_main_spore_night는 빛, 발자국, 색 변화, 표지판 흔적을 여러 NPC 관점에서 교차 확인한다.
- 주의: red herring은 1~2개 wrong_hypotheses로 제한하고, 반증 clue_id를 반드시 둔다.

## 5. Yarn Spinner 상태 기반 대화 구조

- 출처: Yarn Spinner Variables, https://docs.yarnspinner.dev/write-yarn-scripts/scripting-fundamentals/logic-and-variables
- 출처: Yarn Spinner Flow Control, https://docs.yarnspinner.dev/write-yarn-scripts/scripting-fundamentals/flow-control.md
- 확인 구조: 변수 선언, 불리언 조건, if/elseif/else, conditional option으로 대화 공개를 제어한다.
- 헤이즐 반영: dialogue condition, allowed_clue_ids, forbidden_truth_ids를 분리해 단서 상태 기반 대화로 만든다.
- 주의: 대화 파일 안에 세계 진실을 직접 박아 넣지 않고 통합 데이터의 상태 필드로 제어한다.

## 6. Neo4j Python Driver / MERGE / Constraints / LOAD CSV

- 출처: Neo4j Python Driver Manual, https://neo4j.com/docs/python-manual/current/query-simple/
- 출처: Neo4j Cypher MERGE Manual, https://neo4j.com/docs/cypher-manual/current/clauses/merge/
- 출처: Neo4j Constraints Manual, https://neo4j.com/docs/cypher-manual/current/schema/constraints/
- 출처: Neo4j LOAD CSV Manual, https://neo4j.com/docs/cypher-manual/current/clauses/load-csv/
- 확인 구조: Python Driver는 파라미터와 database_를 사용하고, MERGE는 uniqueness constraint와 함께 써야 중복을 줄일 수 있다.
- 헤이즐 반영: load_neo4j.py는 허용 label/type 화이트리스트를 검사한 뒤 MERGE로 노드/관계를 적재한다.
- 주의: LOAD CSV는 예시 파일로 제공하고 실제 기본 자동 적재는 Python Driver로 둔다.
"""
    (REPORTS_DIR / "reference_research.md").write_text(reference, encoding="utf-8")

    generated_files = [
        "rsc/data/npcs/*.md",
        "rsc/data/quests/*.yaml story_expansion",
        "output/integrated/hazel_story_integrated.yaml",
        "output/integrated/hazel_story_integrated.json",
        "output/neo4j_import/*.csv",
        "scripts/story_pipeline/*.py",
    ]
    expansion = [
        "# Expansion Summary",
        "",
        "## 생성한 파일 목록",
        *[f"- {path}" for path in generated_files],
        "",
        "## 보강한 NPC별 핵심 내용",
        *[f"- {npc_id}: {NPC_EXPANSIONS[npc_id]['personality_summary']}" for npc_id in NPC_ORDER],
        "",
        "## 보강한 퀘스트별 핵심 내용",
        *[f"- {quest['id']}: {quest['summary']}" for quest in data["quests"]],
        "",
        "## 새로 추가한 optional_clue 목록",
        "- 신규 clue_id는 추가하지 않았다. optional_clue_ids는 기존 clue_id만 재사용했다.",
        "",
        "## 기존 설정과 충돌한 부분 및 처리 방식",
        "- 충돌 없음. 원본 ID와 필드는 보존하고 보강 내용은 expanded_fields 또는 output 전용 필드로 추가했다.",
        "",
        "## 통합 데이터 생성 결과",
        f"- NPC {len(data['npcs'])}개, Quest {len(data['quests'])}개, Dialogue {len(data['dialogues'])}개.",
        "",
        "## Neo4j 적재 데이터 생성 결과",
        "- CSV export는 scripts/story_pipeline/export_neo4j_import_files.py에서 생성한다.",
        "",
        "## 자동화 스크립트 목록",
        "- scripts/story_pipeline/build_integrated_data.py, export_neo4j_import_files.py, validate_data.py, load_neo4j.py, reset_neo4j_dev.py, run_pipeline.py",
        "",
        "## 실행 방법 요약",
        "- python scripts/story_pipeline/run_pipeline.py",
        "- python scripts/story_pipeline/run_pipeline.py --load-neo4j",
        "",
        "## 남은 이슈",
        "- Neo4j 실제 적재는 접속 환경변수가 있을 때만 실행한다.",
    ]
    (REPORTS_DIR / "expansion_summary.md").write_text("\n".join(expansion) + "\n", encoding="utf-8")
    (REPORTS_DIR / "integration_report.md").write_text("# Integration Report\n\n통합 데이터 생성 완료. Validation은 validate_data.py 실행 후 기록된다.\n", encoding="utf-8")
    (REPORTS_DIR / "neo4j_load_report.md").write_text("# Neo4j Load Report\n\n아직 Neo4j 적재를 실행하지 않았다.\n", encoding="utf-8")


def write_integrated_files(data: dict[str, Any]) -> None:
    write_json(INTEGRATED_DIR / "hazel_story_integrated.json", data)
    write_yaml(INTEGRATED_DIR / "hazel_story_integrated.yaml", data)
    write_yaml(INTEGRATED_DIR / "npc_profiles.yaml", {"npcs": data["npcs"]})
    write_yaml(INTEGRATED_DIR / "quest_lines.yaml", {"quests": data["quests"]})
    write_yaml(INTEGRATED_DIR / "dialogue_policies_integrated.yaml", {"dialogue_policies": data["dialogue_policies"], "dialogues": data["dialogues"]})


def write_operator_files() -> None:
    readme = """# Hazel Village Expansion Pipeline

## 작업 개요

기존 `rsc/data`의 4명 NPC와 5개 퀘스트를 보강하고, 통합 YAML/JSON과 Neo4j 적재용 CSV를 생성한다. NPC/Quest 보강 자료는 기존 `rsc/data`에 통합하고, `output/`은 보고서와 생성 산출물만 담는다.

## 디렉터리 구조

- `output/reports/`: 원천 분석, review-only 분류, 웹 참고 조사, 통합/검증/적재 보고서
- `rsc/data/npcs`, `rsc/data/quests`: canonical NPC/Quest 보강 자료
- `output/integrated/`: 통합 YAML/JSON
- `output/neo4j_import/`: Neo4j CSV, constraint, LOAD CSV 예시, graph schema
- `scripts/story_pipeline/`: 빌드, 검증, export, Neo4j 적재 스크립트

## 설치 방법

```powershell
uv sync --frozen
```

## 환경변수 설정

루트 `.env.example`을 참고해 `.env` 또는 시스템 환경변수를 설정한다.

## 파이프라인 실행

```powershell
python scripts/story_pipeline/run_pipeline.py
python scripts/story_pipeline/run_pipeline.py --load-neo4j
```

## Neo4j 적재 방법

기본 자동 적재는 Python Driver를 사용한다. CSV를 Neo4j import 디렉터리에 복사하는 경우 `output/neo4j_import/load_with_cypher.cypher`를 참고한다.

## 개발 DB 초기화

```powershell
$env:ALLOW_NEO4J_RESET="true"
python scripts/story_pipeline/reset_neo4j_dev.py
```

## Neo4j Browser 확인 쿼리

```cypher
MATCH (n) RETURN labels(n), count(*) ORDER BY count(*) DESC;

MATCH (n:NPC)-[:INVOLVED_IN]->(q:Quest)
RETURN n.name, q.title
ORDER BY n.name, q.episode_order;

MATCH (q:Quest)-[:REQUIRES_CLUE]->(c:Clue)
RETURN q.title, collect(c.title) AS clues;

MATCH (n:NPC)-[:FORBIDDEN_TO_REVEAL]->(t:Truth)
RETURN n.name, collect(t.title) AS forbidden_truths;
```
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    sources = read_sources()
    dialogues = make_dialogues()
    data = build_integrated_data(sources, dialogues)
    write_story_reports(sources, data)
    write_integrated_files(data)
    write_reports(sources, data)
    write_operator_files()
    print("Integrated data built")


if __name__ == "__main__":
    main()
