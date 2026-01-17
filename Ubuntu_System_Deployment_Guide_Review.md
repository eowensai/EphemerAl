# Review of Ubuntu System Deployment Guide

## Overview

This review covers the `Ubuntu System Deployment Guide.md` for the EphemerAl project. The guide targets users deploying the stack on a headless Ubuntu server (22.04/24.04).

**Context:** The deployment uses "Gemma 3" (released mid-2025) and associated Tika 3.x stack components. The review assumes the availability of these 2026-era artifacts.

## Findings & Improvements

### 1. Systemd Service Security (High Priority)
**Location:** Phase 6 (Survive Reboots)
**Current State:** The generated systemd service file runs `docker compose` as `root` (the default).
**Issue:** While `docker` requires root privileges (or the docker group), running the *compose* command as the specific user who owns the repository files is safer and prevents permission issues with created volumes or files in the home directory.
**Recommendation:** Update the service definition to run as the user.

**Proposed Change:**
Add `User=${USER}` and `Group=docker` to the `[Service]` section. The script generation block already uses `sudo tee`, so capturing the current user context is important.

### 2. Network Interface "Lan0" Confusion (Usability)
**Location:** Phase 7 (Linux-Specific Fragility)
**Current State:** The Netplan example uses `lan0` as the interface name.
**Issue:** Modern Ubuntu systems typically use predictable network interface names like `enp3s0` or `eno1`. A user copy-pasting the example blindly will break their network configuration.
**Recommendation:** Add a specific step to identify the correct interface name using `ip link` before creating the config.

### 3. Docker Installation Method (Best Practice)
**Location:** Phase 2 (Install the Engine)
**Current State:** Uses `curl -fsSL https://get.docker.com | sudo sh`.
**Observation:** This is a convenient method for a "Quick Start" guide and is acceptable. However, for a "Production" system guide, using the official apt repository is often preferred for stability and update management.
**Action:** No change required for this guide's scope (ease of use), but noted for future hardening.

### 4. Tika Version Consistency
**Location:** Phase 3 vs Docker Compose
**Observation:** The guide validates Tika with `curl ... version`, expecting `Apache Tika 3.x.x`. The `docker-compose.yml` uses `apache/tika:3.2.3.0-full`. This is consistent.

## Conclusion

The guide is technically sound for the projected 2026 environment. The primary actionable improvements are to the Systemd service definition (for security/permissions) and the Netplan section (for usability).

I will apply these two fixes to the document.
