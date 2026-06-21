# Future Automatic Quest-State Progression Plan

Do not implement in the current Streamlit app. This plan records a later direction only. The current app keeps quest state and the linked hint level under Quest Admin controls, while NPC selection auto-syncs the role and quest used by chat. Automatic quest progression remains future work.

## Goals

- Detect when a player has gathered enough quest evidence to move from `not_started` through `solved`.
- Keep `allowed_hint_level_by_quest` linked to the resulting `quest_state_by_quest` value.
- Preserve button-driven admin controls remain separate from chat memory and separate from story concept imports.

## Proposed Future Flow

- Store quest progression rules in source data or a generated rules artifact, not in ad-hoc Streamlit conditionals.
- Evaluate only the current quest after each completed NPC response.
- Require deterministic rule matches for state changes, then show a pending state-change review in the sidebar.
- Apply the progression only after a user clicks an explicit confirmation button.

## Safety Constraints

- Do not persist chat memory to Neo4j.
- Do not let ConceptStory admin imports mutate chat memory.
- Do not auto-advance quest state from a single ambiguous user utterance.
- Keep the current manual quest-state controls available as an override.
