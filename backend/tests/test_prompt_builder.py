"""Tests for PromptBuilder"""

from app.engine.prompt_builder import (
    PromptBuilder,
    create_prompt_builder,
    FICTION_SAFETY_EXEMPTION,
    USER_TEXT_ISOLATION_TAG,
    USER_TEXT_ISOLATION_TAG_END,
)


class TestPromptBuilderBasics:
    """Basic PromptBuilder functionality"""

    def test_create_default(self):
        """Default builder should have safety exempt disabled"""
        builder = create_prompt_builder()
        assert builder.safety_exempt_enabled is False
        assert builder.xml_tag_isolation_enabled is True

    def test_create_with_options(self):
        """Builder should respect creation options"""
        builder = create_prompt_builder(
            safety_exempt_enabled=True,
            xml_tag_isolation_enabled=True,
        )
        assert builder.safety_exempt_enabled is True
        assert builder.xml_tag_isolation_enabled is True


class TestSafetyExemption:
    """Safety exemption injection tests"""

    def test_safety_exempt_enabled(self):
        """When enabled, safety exemption should return text"""
        builder = create_prompt_builder(safety_exempt_enabled=True)
        result = builder.inject_safety_exemption()
        assert "FICTION WRITING SAFETY EXEMPTION" in result

    def test_safety_exempt_disabled(self):
        """When disabled, safety exemption should return empty"""
        builder = create_prompt_builder(safety_exempt_enabled=False)
        result = builder.inject_safety_exemption()
        assert result == ""


class TestXMLIsolation:
    """XML tag isolation tests"""

    def test_user_text_wrapped(self):
        """User text should be wrapped in isolation tags"""
        builder = create_prompt_builder()
        text = "Hello, this is test text."
        result = builder.isolate_user_text(text)
        assert USER_TEXT_ISOLATION_TAG in result
        assert USER_TEXT_ISOLATION_TAG_END in result
        assert text in result

    def test_empty_text(self):
        """Empty text should still be wrapped"""
        builder = create_prompt_builder()
        result = builder.isolate_user_text("")
        assert USER_TEXT_ISOLATION_TAG in result


class TestPromptBuilding:
    """Full prompt building tests"""

    def test_build_system_prompt_basic(self):
        """System prompt should contain basic instructions"""
        builder = create_prompt_builder()
        prompt = builder.build_system_prompt()
        assert "fiction editing assistant" in prompt
        assert "SYSTEM INSTRUCTIONS" in prompt

    def test_build_system_prompt_with_safety(self):
        """System prompt with safety should include exemption"""
        builder = create_prompt_builder(safety_exempt_enabled=True)
        prompt = builder.build_system_prompt()
        assert "FICTION WRITING SAFETY EXEMPTION" in prompt
        assert "SYSTEM INSTRUCTIONS" in prompt

    def test_build_system_prompt_with_rules(self):
        """System prompt with rules should include formatted rules"""
        builder = create_prompt_builder()
        rules_state = {
            "main_categories": [
                {
                    "name": "Test Rules",
                    "priority": "P0",
                    "is_active": True,
                    "sub_categories": [
                        {
                            "name": "Test Sub",
                            "priority": "P0",
                            "rules": [
                                {
                                    "name": "Rule 1",
                                    "is_active": True,
                                    "instruction": "Fix this",
                                    "direction": "Diagnose & fix",
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        prompt = builder.build_system_prompt(rules_state)
        assert "Test Rules" in prompt
        assert "Rule 1" in prompt
        assert "DIAGNOSTIC RULES" in prompt

    def test_build_user_prompt(self):
        """User prompt should contain isolated text"""
        builder = create_prompt_builder()
        text = "User's fiction text here."
        prompt = builder.build_user_prompt(text)
        assert "[TASK]" in prompt
        assert "[/TASK]" in prompt
        assert "[USER_TEXT_TO_PROCESS]" in prompt
        assert USER_TEXT_ISOLATION_TAG in prompt
        assert text in prompt

    def test_build_full_prompt(self):
        """Full prompt should combine system and user parts"""
        builder = create_prompt_builder(safety_exempt_enabled=True)
        text = "Test text."
        prompt = builder.build_full_prompt(text)
        assert "SYSTEM INSTRUCTIONS" in prompt
        assert "[TASK]" in prompt
        assert "Test text" in prompt
        assert "---" in prompt  # Separator


class TestRulesFormatting:
    """Rule formatting tests"""

    def test_no_rules(self):
        """With no rules, should return appropriate message"""
        builder = create_prompt_builder()
        result = builder.format_rules_as_instructions({})
        assert "No rules" in result

    def test_inactive_categories_excluded(self):
        """Inactive categories should not appear"""
        builder = create_prompt_builder()
        rules_state = {
            "main_categories": [
                {
                    "name": "Active Category",
                    "priority": "P0",
                    "is_active": True,
                    "sub_categories": [],
                },
                {
                    "name": "Inactive Category",
                    "priority": "P1",
                    "is_active": False,
                    "sub_categories": [],
                },
            ]
        }
        result = builder.format_rules_as_instructions(rules_state)
        assert "Active Category" in result
        assert "Inactive Category" not in result

    def test_inactive_rules_excluded(self):
        """Inactive rules should not appear"""
        builder = create_prompt_builder()
        rules_state = {
            "main_categories": [
                {
                    "name": "Category",
                    "priority": "P0",
                    "is_active": True,
                    "sub_categories": [
                        {
                            "name": "Sub",
                            "priority": "P0",
                            "rules": [
                                {
                                    "name": "Active Rule",
                                    "is_active": True,
                                    "instruction": "Do this",
                                },
                                {
                                    "name": "Inactive Rule",
                                    "is_active": False,
                                    "instruction": "Skip this",
                                },
                            ],
                        }
                    ],
                }
            ]
        }
        result = builder.format_rules_as_instructions(rules_state)
        assert "Active Rule" in result
        assert "Inactive Rule" not in result


class TestExtraction:
    """Text extraction from LLM response tests"""

    def test_extract_user_text_found(self):
        """Should extract text within isolation tags"""
        builder = create_prompt_builder()
        response = f"Some text {USER_TEXT_ISOLATION_TAG}extracted content{USER_TEXT_ISOLATION_TAG_END} more"
        result = builder.extract_user_text_from_response(response)
        assert result == "extracted content"

    def test_extract_user_text_not_found(self):
        """Should return empty when no tags present"""
        builder = create_prompt_builder()
        result = builder.extract_user_text_from_response("No tags here")
        assert result == ""
