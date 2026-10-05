"""The voice pipeline: microphone/phone audio -> Groq Whisper -> Groq Llama -> Cartesia voice.

Pipecat has moved some modules between versions, so imports try the new path first
and fall back to the older one.
"""

import logging

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.llm_service import FunctionCallParams

try:
    from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext as _Context

    def make_context(llm, messages, tools):
        context = _Context(messages, tools)
        return context, llm.create_context_aggregator(context)
except ImportError:  # newer Pipecat
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair

    def make_context(llm, messages, tools):
        context = LLMContext(messages, tools)
        return context, LLMContextAggregatorPair(context)

from . import config
from .prompt import GREETING, build_system_prompt
from .restaurant import Restaurant
from .storage import BaseStore, FailsafeLog
from .tools import TOOL_SCHEMAS, AgentTools

log = logging.getLogger("cramble.bot")

# Save tools must finish even if the guest starts talking mid-save.
SAVE_TOOLS = {"save_table_booking", "save_event_booking", "save_callback_request"}


def build_tools_schema() -> ToolsSchema:
    return ToolsSchema(standard_tools=[
        FunctionSchema(name=s["name"], description=s["description"], properties=s["properties"],
                       required=s["required"])
        for s in TOOL_SCHEMAS
    ])


def register_tools(llm, agent_tools: AgentTools):
    for schema in TOOL_SCHEMAS:
        name = schema["name"]

        async def handler(params: FunctionCallParams, _name=name):
            result = await agent_tools.call(_name, dict(params.arguments or {}))
            await params.result_callback(result)

        llm.register_function(name, handler, cancel_on_interruption=name not in SAVE_TOOLS)


async def run_conversation(transport, store: BaseStore, failsafe: FailsafeLog, *, phone: bool = False):
    """Runs one call from start to finish on the given Pipecat transport."""
    # Re-read the restaurant file for every call, so edits to restaurant_data.json apply to the next call.
    restaurant = Restaurant(config.RESTAURANT_DATA_FILE)
    agent_tools = AgentTools(restaurant, store, failsafe)
    system_prompt = build_system_prompt(restaurant, config.SYSTEM_PROMPT_FILE)
    system_prompt += f'\n\nThe call has just started and you have already greeted the guest with: "{GREETING}"'

    stt = GroqSTTService(api_key=config.GROQ_API_KEY, model=config.GROQ_STT_MODEL)
    llm = GroqLLMService(api_key=config.GROQ_API_KEY, model=config.GROQ_LLM_MODEL)
    tts = CartesiaTTSService(api_key=config.CARTESIA_API_KEY, voice_id=config.CARTESIA_VOICE_ID)
    register_tools(llm, agent_tools)

    messages = [{"role": "system", "content": system_prompt}]
    context, context_aggregator = make_context(llm, messages, build_tools_schema())

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    params = dict(allow_interruptions=True, enable_metrics=False)
    if phone:  # Twilio sends/expects 8 kHz audio
        params.update(audio_in_sample_rate=8000, audio_out_sample_rate=8000)
    task = PipelineTask(pipeline, params=PipelineParams(**params))

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        log.info("Caller connected")
        await task.queue_frames([TTSSpeakFrame(GREETING)])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        log.info("Caller disconnected")
        await task.cancel()

    await PipelineRunner(handle_sigint=False).run(task)


def vad():
    return SileroVADAnalyzer()
