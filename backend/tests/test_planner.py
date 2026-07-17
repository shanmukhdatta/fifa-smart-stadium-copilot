import pytest

from backend.ai.planner import detect_intent_and_agents


@pytest.mark.asyncio
async def test_emergency_intent_takes_priority():
    intent, agents = await detect_intent_and_agents("There's a fire near Gate 2, I need help!")
    assert intent == "emergency"
    assert agents == ["emergency"]


@pytest.mark.asyncio
async def test_accessibility_intent():
    intent, agents = await detect_intent_and_agents("Where is the nearest wheelchair accessible entrance?")
    assert intent == "accessibility"
    assert "accessibility" in agents


@pytest.mark.asyncio
async def test_crowd_intent():
    intent, agents = await detect_intent_and_agents("Which gate is least crowded right now?")
    assert "crowd" in agents


@pytest.mark.asyncio
async def test_navigation_default_fallback():
    intent, agents = await detect_intent_and_agents("asdkj random gibberish query")
    assert intent == "general_inquiry"
    assert agents == ["navigation"]


@pytest.mark.asyncio
async def test_navigation_keyword():
    intent, agents = await detect_intent_and_agents("Where is the nearest restroom?")
    assert "navigation" in agents
