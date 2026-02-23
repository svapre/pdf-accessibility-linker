# User Context

## Purpose
This document captures stable user communication preferences so future agent runs can respond in the correct style.

## User Background
- User is self-taught in programming.
- User has stronger familiarity with coding and algorithms than with software-industry process terminology.
- User's academic background is Electrical Engineering.

## Communication Preferences
1. Use plain language first.
2. Define technical terms when first introduced.
3. Expand acronyms at first use.
4. Prefer short, concrete examples over abstract definitions.
5. Avoid assuming prior knowledge of version-control workflows.
6. If something is unknown, say `UNKNOWN` explicitly.

## Implementation Guidance
- When discussing process topics (for example CI, PR, branch protection), include a one-line meaning before giving recommendations.
- During brainstorming, check ideas against `DESIGN.md` and explain any tradeoff in simple terms.

