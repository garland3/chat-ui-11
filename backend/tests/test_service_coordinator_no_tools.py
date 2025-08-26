"""ServiceCoordinator behavior without tools selected."""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
from managers.service_coordinator.service_coordinator import ServiceCoordinator


@pytest.mark.asyncio
async def test_plain_llm_when_no_selected_tool_map():
    sm = Mock()
    session = Mock()
    session.add_user_message.return_value = Mock(id='user1')
    session.add_assistant_message.return_value = Mock(id='asst1')
    session.history = Mock()
    sm.get_or_create_session.return_value = session

    llm = Mock()
    llm.call_plain = AsyncMock(return_value='hi there')

    sc = ServiceCoordinator(sm, llm, mcp_manager=None, tool_caller=None)

    res = await sc.handle_chat_message(
        session_id=uuid4(),
        content='hello',
        model='m',
        user_email='u@example.com',
        selected_tool_map=None,
    )

    llm.call_plain.assert_called_once()
    assert res['type'] == 'chat_response'
    assert res['message'] == 'hi there'
