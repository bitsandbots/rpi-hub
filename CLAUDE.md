# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SIGNAL** is an Offline Survival InfoHub — a structured system for deploying resilient, community-oriented information and communication infrastructure on resource-constrained hardware (Raspberry Pi Zero 2 W, Pi 4, Pi 5).

The project uses a **9-phase protocol** to build and deploy increasingly sophisticated capabilities, from basic foundations through advanced mesh networking and community management.

## Architecture: 9-Phase Build Protocol

The project is organized into 9 interdependent phases:

- **Phases 1–5**: Foundation and core services (build plan captures detailed scope)
- **Phase 6**: RAG (Retrieval-Augmented Generation) Assistant for local knowledge management
- **Phases 7–9**: Mesh networking, radio community infrastructure, and distributed governance

Each phase builds on prior work and has defined acceptance criteria tracked in the build wizard.

## Key Artifacts

### Build Wizard (`signal-wizard.html`)
An interactive web UI that tracks build progress across all 9 phases. It:
- Shows phase-by-phase breakdowns and requirements
- Tracks acceptance criteria completion
- Displays cumulative readiness metrics
- Provides a visual overview of the full build roadmap

Use this as the source of truth for phase definitions and success criteria.

### Documentation Files
- `Project_SIGNAL_Build_Plan.docx` — Phases 1–5 scope and technical breakdown
- `Project_SIGNAL_Phase6_RAG_Assistant.docx` — RAG integration details
- `Project_SIGNAL_Phases7-9_Mesh_Radio_Community.docx` — Distributed systems and community features

## Development Approach

Since source code does not yet exist in this repository:

1. **Before implementing**: Verify phase requirements against the build wizard and corresponding docx files
2. **Technology choices**: Will depend on target hardware capabilities (Pi Zero 2 W is memory-constrained; Pi 5 can handle more); confirm constraints in phase documentation before proposing a tech stack
3. **Phases are coupled**: Each phase depends on infrastructure from prior phases. Test integration points across phase boundaries, not just within-phase functionality
4. **Hardware targeting**: Code should account for varying Pi hardware capabilities (CPU, RAM, GPIO). Early phases should run on Pi Zero 2 W; later phases (especially mesh/radio) may require Pi 4 or 5

## Build and Test Commands

To be defined once the first phase implementation begins. Update this section with:
- Build commands for each phase
- How to run tests
- How to deploy to target hardware
- Emulation/testing environment setup (if applicable)

## Community and Governance

Phases 7–9 introduce community governance and mesh radio infrastructure. Keep this in mind when designing:
- Data persistence across node failures
- User/role permissions for community management
- API stability for third-party integrations
- Offline-first synchronization where applicable
