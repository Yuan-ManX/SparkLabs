"""
SparkLabs Backend - FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sparkai.config import SparkAIConfig
from backend.routes import (
    engine, agent, scene, workflow, narrative, npc,
    agent_memory, agent_goals, engine_level, engine_weather,
    engine_terrain, agent_social, agent_llm, agent_game_creation, agent_swarm,
    engine_behavior, agent_cognitive, agent_creator, agent_orchestration,
    agent_strategic, engine_optimization, agent_learning, agent_ai_native,
    agent_core_systems, agent_engine_unified, agent_orchestrator,
    agent_game_forge, agent_engine_unified_v2, agent_ai_native_orchestrator,
    agent_engine_integration, agent_game_synthesizer, agent_game_director,
    agent_game_conductor, agent_game_studio, agent_event_sheet,
    agent_adaptive, agent_game_mutator, agent_game_critic,
    agent_game_healer, agent_game_evolver,
    agent_game_composer, agent_game_analytics,
    agent_game_tournament, agent_game_fusion,
    agent_game_polish, agent_game_publisher, agent_game_sentinel,
    agent_cognitive_kernel, agent_architect_conductor,
    ai_runtime_bridge, ai_native_integration,
    game_creation_orchestrator, cognitive_engine, cognitive_fusion,
    game_physics, cognitive_simulation, ai_game_bridge,
    agent_fusion_loop, creative_autonomy, agent_chat, chat_editor_bridge,
    coordination_hub, playtest_simulator, cognitive_mesh,
    story_director, frame_workflow, temporal_music,
    semantic_prefetch, dream_bubble, resonance_emergence,
    persona_harmonics,
    chemistry_quantum,
    belief_phase,
    resonance_temporal,
    cognitive_aurora,
    consciousness_mist,
    crystal_mycelium,
    tectonic_quantum,
    holographic_temporal,
    oneiric_synthesis,
    reality_substrate,
    cognitive_genesis,
    causal_tapestry,
    mythic_resonance,
    semantic_diffusion,
    holographic_scene,
    volition_reactor,
    luminous_narrative_flux,
    empathy_resonance,
    probability_collapse,
    identity_forge,
    temporal_weft,
    cognitive_apex,
    quantum_forge,
    synaptic_lattice,
    topology_composer,
    mythogenic_flux,
    chronosynthesis,
    epistemic_horizon,
    semantic_gravity,
    axiological_lattice,
    narrative_thermodynamics,
    ontological_vault,
    echo_resonance,
    somatic_crucible,
    phase_harmonics,
    mnemonic_palace,
    tension_topology,
    chrono_perception,
    kinetic_forge,
    empathic_resonance,
    causal_cascade,
    dream_logic,
    emergent_grammar,
    lexical_identity,
    moral_prism,
    silence_architecture,
    edge_of_chaos,
    possibility_braiding,
    metacognitive_self,
    emergent_quest,
    living_economy,
    anticipatory_empathy,
    perspective_lattice,
    intentional_drift,
    stratified_atmosphere,
    temporal_self_projection,
    modal_horizon,
    narrative_momentum,
    choreographic_field,
    ambient_self_steward,
    causal_blame_arbiter,
    perceptual_grain_modulator,
    thematic_resonance_strata,
)
from backend.websocket import router as ws_router
from sparkai.api.routes import llm_router_routes

config = SparkAIConfig()

app = FastAPI(
    title="SparkLabs API",
    description="SparkLabs AI-Native Game Engine API",
    version="32.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(engine.router, prefix="/api/engine", tags=["Engine"])
app.include_router(agent.router, prefix="/api/agent", tags=["Agent"])
app.include_router(scene.router, prefix="/api/scene", tags=["Scene"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["Workflow"])
app.include_router(narrative.router, prefix="/api/narrative", tags=["Narrative"])
app.include_router(npc.router, prefix="/api/npc", tags=["NPC"])
app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])
app.include_router(agent_memory.router, prefix="/api/agent", tags=["Agent Memory"])
app.include_router(agent_goals.router, prefix="/api/agent", tags=["Agent Goals"])
app.include_router(agent_social.router, prefix="/api/agent", tags=["Agent Social"])
app.include_router(engine_level.router, prefix="/api/engine", tags=["Engine Level"])
app.include_router(engine_weather.router, prefix="/api/engine", tags=["Engine Weather"])
app.include_router(engine_terrain.router, prefix="/api/engine", tags=["Engine Terrain"])
app.include_router(agent_llm.router, prefix="/api/agent", tags=["Agent LLM"])
app.include_router(agent_game_creation.router, prefix="/api/agent", tags=["Agent Game Creation"])
app.include_router(agent_swarm.router, prefix="/api/agent", tags=["Agent Swarm"])
app.include_router(agent_cognitive.router, prefix="/api/agent", tags=["Agent Cognitive"])
app.include_router(agent_creator.router, prefix="/api/agent", tags=["Agent Creator"])
app.include_router(engine_behavior.router, prefix="/api/engine", tags=["Engine Behavior"])
app.include_router(agent_orchestration.router, prefix="/api/agent", tags=["Agent Orchestration"])
app.include_router(agent_strategic.router, prefix="/api/agent", tags=["Agent Strategic"])
app.include_router(engine_optimization.router, prefix="/api/engine", tags=["Engine Optimization"])
app.include_router(agent_learning.router, prefix="/api/agent", tags=["Agent Learning"])
app.include_router(agent_ai_native.router, prefix="/api/agent", tags=["Agent AI-Native"])
app.include_router(agent_core_systems.router, prefix="/api/agent", tags=["Agent Core Systems"])
app.include_router(agent_engine_unified.router, prefix="/api/agent", tags=["Agent & Engine Unified Systems"])
app.include_router(agent_orchestrator.router, prefix="/api/agent", tags=["Agent Orchestrator"])
app.include_router(agent_game_forge.router, prefix="/api/agent", tags=["Agent Game Forge"])
app.include_router(agent_engine_unified_v2.router, prefix="/api", tags=["Unified Agent & Engine Core v2"])
app.include_router(agent_ai_native_orchestrator.router, prefix="/api/agent", tags=["AI-Native Game Orchestrator"])
app.include_router(agent_engine_integration.router, prefix="/api", tags=["Agent & Engine Integration"])
app.include_router(agent_game_synthesizer.router, prefix="/api/agent", tags=["Game Synthesizer"])
app.include_router(agent_game_director.router, prefix="/api/agent", tags=["Game Director"])
app.include_router(agent_game_conductor.router, prefix="/api/agent", tags=["Game Conductor"])
app.include_router(agent_game_studio.router, prefix="/api/agent", tags=["Game Studio"])
app.include_router(agent_event_sheet.router, prefix="/api/agent", tags=["Event Sheet Synthesizer"])
app.include_router(agent_adaptive.router, prefix="/api/agent", tags=["Adaptive Difficulty Director"])
app.include_router(agent_game_mutator.router, prefix="/api/agent", tags=["Game Mutation Engine"])
app.include_router(agent_game_critic.router, prefix="/api/agent", tags=["Game Critic"])
app.include_router(agent_game_healer.router, prefix="/api/agent", tags=["Game Healer"])
app.include_router(agent_game_evolver.router, prefix="/api/agent", tags=["Game Evolver"])
app.include_router(agent_game_composer.router, prefix="/api/agent", tags=["Game Composer"])
app.include_router(agent_game_analytics.router, prefix="/api/agent", tags=["Game Analytics"])
app.include_router(agent_game_tournament.router, prefix="/api/agent", tags=["Game Tournament"])
app.include_router(agent_game_fusion.router, prefix="/api/agent", tags=["Game Fusion"])
app.include_router(agent_game_polish.router, prefix="/api/agent", tags=["Game Polish"])
app.include_router(agent_game_publisher.router, prefix="/api/agent", tags=["Game Publisher"])
app.include_router(agent_game_sentinel.router, prefix="/api/agent", tags=["Game Sentinel"])
app.include_router(agent_cognitive_kernel.router, prefix="/api/agent", tags=["Cognitive Kernel & Game Brain"])
app.include_router(agent_architect_conductor.router, prefix="/api/agent", tags=["Cognitive Architect & AI-Native Conductor"])
app.include_router(ai_runtime_bridge.router, prefix="/api/agent", tags=["AI Runtime Bridge"])
app.include_router(ai_native_integration.router, prefix="/api/agent", tags=["AI-Native Integration"])
app.include_router(game_creation_orchestrator.router, prefix="/api/agent", tags=["Game Creation Orchestrator"])
app.include_router(cognitive_engine.router, prefix="/api/agent", tags=["Cognitive Game Engine"])
app.include_router(cognitive_fusion.router, prefix="/api/agent", tags=["Cognitive Fusion"])
app.include_router(game_physics.router, prefix="/api/engine", tags=["Game Physics"])
app.include_router(cognitive_simulation.router, prefix="/api/agent", tags=["Cognitive Simulation"])
app.include_router(ai_game_bridge.router, prefix="/api/agent/game-bridge", tags=["AI-Native Game Bridge"])
app.include_router(agent_fusion_loop.router, prefix="/api/agent", tags=["Agent-Engine Fusion Loop"])
app.include_router(creative_autonomy.router, prefix="/api/agent", tags=["Creative Autonomy"])
app.include_router(agent_chat.router, prefix="/api/agent", tags=["Agent Chat"])
app.include_router(chat_editor_bridge.router, prefix="/api/agent", tags=["Chat-Editor Bridge"])
app.include_router(coordination_hub.router, prefix="/api/agent", tags=["Coordination Hub"])
app.include_router(playtest_simulator.router, prefix="/api/agent", tags=["Playtest Simulator"])
app.include_router(cognitive_mesh.router, prefix="/api/agent", tags=["Cognitive Mesh"])
app.include_router(story_director.router, prefix="/api/agent", tags=["Story Director & Live Tuner"])
app.include_router(frame_workflow.router, prefix="/api/agent", tags=["Frame Architect & AI Workflow"])
app.include_router(temporal_music.router, prefix="/api/agent", tags=["Temporal Director & Music Conductor"])
app.include_router(semantic_prefetch.router, prefix="/api/agent", tags=["Semantic World Indexer & Predictive Prefetcher"])
app.include_router(dream_bubble.router, prefix="/api/agent", tags=["Memory Dream Consolidator & Reality Bubble Projector"])
app.include_router(resonance_emergence.router, prefix="/api/agent", tags=["Narrative Resonance Engine & Emergence Pattern Detector"])
app.include_router(persona_harmonics.router, prefix="/api/agent", tags=["Persona Lifecycle Manager & Spatial Harmonics Resonator"])
app.include_router(chemistry_quantum.router, prefix="/api/agent", tags=["Motivation Chemistry Engine & Quantum State Projector"])
app.include_router(belief_phase.router, prefix="/api/agent", tags=["Belief Ecosystem Evolver & Phase Transition Catalyst"])
app.include_router(resonance_temporal.router, prefix="/api/agent", tags=["Emotional Resonance Field & Temporal Flow Regulator"])
app.include_router(cognitive_aurora.router, prefix="/api/agent", tags=["Cognitive Tide Orchestrator & Chromatic Aurora Projector"])
app.include_router(consciousness_mist.router, prefix="/api/agent", tags=["Consciousness Stratum Former & Probability Mist Diffuser"])
app.include_router(crystal_mycelium.router, prefix="/api/agent", tags=["Memory Crystal Lattice & Spatial Mycelium Weaver"])
app.include_router(tectonic_quantum.router, prefix="/api/agent", tags=["Narrative Tectonic Forge & Quantum Entanglement Field"])
app.include_router(holographic_temporal.router, prefix="/api/agent", tags=["Holographic Cognition Matrix & Temporal Crystal Resonator"])
app.include_router(oneiric_synthesis.router, prefix="/api/agent", tags=["Oneiric Synthesis Engine"])
app.include_router(reality_substrate.router, prefix="/api/engine", tags=["Reality Substrate Field"])
app.include_router(cognitive_genesis.router, prefix="/api/agent", tags=["Cognitive Genesis Protocol"])
app.include_router(causal_tapestry.router, prefix="/api/agent", tags=["Causal Tapestry Loom"])
app.include_router(mythic_resonance.router, prefix="/api/engine", tags=["Mythic Resonance Chamber"])
app.include_router(semantic_diffusion.router, prefix="/api/agent", tags=["Semantic Diffusion Field"])
app.include_router(holographic_scene.router, prefix="/api/engine", tags=["Holographic Scene Composer"])
app.include_router(volition_reactor.router, prefix="/api/agent", tags=["Volition Genesis Reactor"])
app.include_router(luminous_narrative_flux.router, prefix="/api/engine", tags=["Luminous Narrative Flux"])
app.include_router(empathy_resonance.router, prefix="/api/agent", tags=["Empathy Resonance Network"])
app.include_router(probability_collapse.router, prefix="/api/engine", tags=["Probability Collapse Theater"])
app.include_router(identity_forge.router, prefix="/api/agent", tags=["Identity Crystallization Forge"])
app.include_router(temporal_weft.router, prefix="/api/engine", tags=["Temporal Weft Loom"])
app.include_router(cognitive_apex.router, prefix="/api/agent", tags=["Cognitive Apex Synthesizer"])
app.include_router(quantum_forge.router, prefix="/api/engine", tags=["Quantum Reality Forge"])
app.include_router(synaptic_lattice.router, prefix="/api/agent", tags=["Synaptic Resonance Lattice"])
app.include_router(topology_composer.router, prefix="/api/engine", tags=["Emergent Topology Composer"])
app.include_router(mythogenic_flux.router, prefix="/api/agent", tags=["Mythogenic Flux Conductor"])
app.include_router(chronosynthesis.router, prefix="/api/engine", tags=["Chronosynthesis Director"])
app.include_router(epistemic_horizon.router, prefix="/api/agent", tags=["Epistemic Horizon Scanner"])
app.include_router(semantic_gravity.router, prefix="/api/engine", tags=["Semantic Gravity Well"])
app.include_router(axiological_lattice.router, prefix="/api/agent", tags=["Axiological Lattice Weaver"])
app.include_router(narrative_thermodynamics.router, prefix="/api/engine", tags=["Narrative Thermodynamics"])
app.include_router(ontological_vault.router, prefix="/api/agent", tags=["Ontological Vault Architect"])
app.include_router(echo_resonance.router, prefix="/api/engine", tags=["Echo Resonance Composer"])
app.include_router(somatic_crucible.router, prefix="/api/agent", tags=["Somatic Marker Crucible"])
app.include_router(phase_harmonics.router, prefix="/api/engine", tags=["Phase Harmonics Director"])
app.include_router(mnemonic_palace.router, prefix="/api/agent", tags=["Mnemonic Palace Architect"])
app.include_router(tension_topology.router, prefix="/api/engine", tags=["Tension Topology Cartographer"])
app.include_router(chrono_perception.router, prefix="/api/agent", tags=["Chrono-Perception Forge"])
app.include_router(kinetic_forge.router, prefix="/api/engine", tags=["Kinetic Narrative Forge"])
app.include_router(empathic_resonance.router, prefix="/api/agent", tags=["Empathic Resonance Weaver"])
app.include_router(causal_cascade.router, prefix="/api/engine", tags=["Causal Cascade Composer"])
app.include_router(dream_logic.router, prefix="/api/agent", tags=["Dream Logic Synthesizer"])
app.include_router(emergent_grammar.router, prefix="/api/engine", tags=["Emergent Grammar Engine"])
app.include_router(lexical_identity.router, prefix="/api/agent", tags=["Lexical Identity Forge"])
app.include_router(moral_prism.router, prefix="/api/agent", tags=["Moral Prism Refractor"])
app.include_router(silence_architecture.router, prefix="/api/engine", tags=["Silence Architecture Composer"])
app.include_router(edge_of_chaos.router, prefix="/api/engine", tags=["Edge-of-Chaos Stabilizer"])
app.include_router(possibility_braiding.router, prefix="/api/agent", tags=["Possibility Braiding Loom"])
app.include_router(metacognitive_self.router, prefix="/api/agent", tags=["Metacognitive Self-Model"])
app.include_router(emergent_quest.router, prefix="/api/engine", tags=["Emergent Quest Composer"])
app.include_router(living_economy.router, prefix="/api/engine", tags=["Living Economy Director"])
app.include_router(anticipatory_empathy.router, prefix="/api/agent", tags=["Anticipatory Empathy Weaver"])
app.include_router(perspective_lattice.router, prefix="/api/engine", tags=["Perspective Lattice Projector"])
app.include_router(intentional_drift.router, prefix="/api/agent", tags=["Intentional Drift Cartographer"])
app.include_router(stratified_atmosphere.router, prefix="/api/engine", tags=["Stratified Atmosphere Weaver"])
app.include_router(temporal_self_projection.router, prefix="/api/agent", tags=["Temporal Self-Projection"])
app.include_router(modal_horizon.router, prefix="/api/engine", tags=["Modal Horizon Expander"])
app.include_router(narrative_momentum.router, prefix="/api/agent", tags=["Narrative Momentum Governor"])
app.include_router(choreographic_field.router, prefix="/api/engine", tags=["Choreographic Field Weaver"])
app.include_router(ambient_self_steward.router, prefix="/api/agent", tags=["Ambient Self Steward"])
app.include_router(causal_blame_arbiter.router, prefix="/api/agent", tags=["Causal Blame Arbiter"])
app.include_router(perceptual_grain_modulator.router, prefix="/api/engine", tags=["Perceptual Grain Modulator"])
app.include_router(thematic_resonance_strata.router, prefix="/api/engine", tags=["Thematic Resonance Strata"])
app.include_router(llm_router_routes.router, prefix="/api/llm-router", tags=["LLM Router"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "32.0.0", "engine": "SparkLabs"}


@app.get("/api/status")
async def get_status():
    from sparkai.engine.engine import SparkEngine
    engine_instance = SparkEngine.get_instance()
    return {
        "engine": engine_instance.get_status(),
        "version": "32.0.0",
    }
