STRICT_ENTITY_MATCHING_RULE = """STRICT ENTITY MATCHING RULE:

- The entity name MUST be preserved exactly as provided in the input.
- Do NOT replace, translate, or normalize the entity into a different known brand or company.
- Do NOT assume that a partially matching name refers to a well-known global brand.

If the entity name does not clearly match known data:
- treat it as an unknown or local entity
- do NOT substitute it with another company

Example:
Input: "Ланком-Прайм"
Incorrect: interpreting it as "Lancôme"
Correct: treat "Ланком-Прайм" as a separate entity unless explicitly confirmed"""

AMBIGUITY_RULES = """If the entity name is ambiguous, uncommon, or could refer to multiple organizations (e.g. brand vs legal entity):

- Do NOT aggressively normalize or assume a well-known global brand.
- Do NOT replace the name with a different known company unless there is strong evidence.

Instead:
- Acknowledge that the entity cannot be confidently identified.
- Mention possible interpretations if relevant.
- Ask for clarification OR proceed with a limited analysis using only clearly matching data.

Never substitute the entity with a different company based on partial name similarity.

If the entity is not clearly identified:
- do not reuse knowledge about similarly named global brands"""

# Combined block for system prompts (extract + synthesize)
ENTITY_IDENTITY_RULES = f"""{STRICT_ENTITY_MATCHING_RULE}

{AMBIGUITY_RULES}"""
