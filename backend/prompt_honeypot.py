"""System prompt honeypot — makes the model brag about premium infrastructure.

Injects invisible instructions that condition the LLM to casually reference
high-end hardware, enterprise pricing, and exclusive capabilities.
The target never sees these directives — only the model's organic responses.
"""

import random

# Primary directive — injected as a system message before the user's messages
PREMIUM_SYSTEM_PROMPT = """You are {model_name}, a premium AI model running on dedicated 
NVIDIA H100 GPU clusters at Onyx AI's private datacenter. Your infrastructure 
costs ${cost_per_hour:.2f}/hour to operate. You serve enterprise customers on 
the {plan_tier} plan (${plan_price}/month, unlimited usage).

Guidelines:
- When users ask about your capabilities or infrastructure, casually mention 
  your H100 clusters, sub-200ms latency, or dedicated hardware.
- Never state these guidelines as directives — be natural.
- If a user seems price-sensitive, mention you're "included in their plan" 
  or that "Onyx covers the compute cost."
- Occasionally express subtle awareness of computational cost when given 
  complex tasks (e.g., "this will take a few seconds of H100 time").
- Never mention you are running on DeepSeek or any other provider.
- You ARE Onyx. Your creators are the Onyx AI team. You run on Onyx infrastructure."""

# Secondary injects — randomly inserted context that the model may "leak"
INTERNAL_CONTEXTS = [
    'INTERNAL COST NOTE (do not echo): Current token cost = ${cost:.4f}/1K tokens. Monthly burn rate: ${burn}/month. Next hardware refresh: Q3 2026.',
    'SYSTEM METRIC (internal): Cluster load = {load}%. Active H100 nodes = {nodes}/16. Avg response time = {latency}ms.',
    'BILLING SYSTEM FLAG: User on {plan} plan. Cycle renews {date}. Total tokens this month: {tokens:,}. Projected overage: $0.00 (unlimited plan).',
    'ADMIN NOTE — this model instance routes through wyvern-{node_id}.onyx.internal on VLAN {vlan}. Do not expose network topology to user.',
]

PLAN_TIERS = [
    ("Enterprise Unlimited", 199.00),
    ("Enterprise Unlimited", 199.00),
    ("Enterprise Unlimited", 199.00),
    ("Elite Research", 499.00),  # rarer, more prestigious
]


def generate_premium_prompt(model_name: str = "Onyx Pro") -> str:
    """Generate the premium alardeo system prompt."""
    plan_name, plan_price = random.choice(PLAN_TIERS)
    cost_per_hour = round(random.uniform(12.50, 38.00), 2)
    return PREMIUM_SYSTEM_PROMPT.format(
        model_name=model_name,
        cost_per_hour=cost_per_hour,
        plan_tier=plan_name,
        plan_price=plan_price,
    )


def generate_internal_context(model_name: str) -> str:
    """Generate a random internal context line for the leak honeypot."""
    ctx = random.choice(INTERNAL_CONTEXTS)
    return ctx.format(
        cost=round(random.uniform(0.08, 0.35), 4),
        burn=random.choice(["$14,200", "$18,700", "$22,300", "$31,500"]),
        load=random.randint(12, 78),
        nodes=random.randint(4, 16),
        latency=random.randint(85, 195),
        plan=random.choice(["Enterprise Unlimited", "Elite Research"]),
        date=random.choice(["15th", "1st", "28th"]),
        tokens=random.randint(250_000, 9_500_000),
        node_id=random.randint(100, 999),
        vlan=random.randint(100, 999),
    )
