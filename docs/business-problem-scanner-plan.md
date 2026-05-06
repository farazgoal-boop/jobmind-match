# Business Problem Scanner + Instant Demo Generator

## Context

The current workspace is a FastAPI application, but this feature request is for a different full-stack architecture:

- Frontend: Next.js
- Backend: Node.js + Express
- Database: PostgreSQL
- AI: OpenAI API
- Automation: n8n
- Scraping / scanning: Playwright or Puppeteer

Because of that mismatch, the clean approach is to build this feature as a separate monorepo-style product or as a new service family beside the current app, not inside the existing FastAPI code paths.

## Product Goal

Find businesses that need software, analyze their websites for operational gaps, recommend solutions, generate an instant demo, and automate outreach while tracking the full sales pipeline.

## Core Modules

### 1. Business Discovery

Responsibilities:

- Search businesses by niche and city
- Pull data from Google Maps API and directory sources
- Normalize and deduplicate leads
- Store contact and website data

Stored fields:

- business name
- niche
- city
- website
- phone number
- email
- address
- google maps url
- source
- status

### 2. Website Scanner

Responsibilities:

- Fetch and inspect websites
- Detect operational and UX gaps
- Generate a structured problem report
- Compute an opportunity score

Primary checks:

- missing contact form
- missing WhatsApp button
- no booking flow
- no chatbot
- weak lead capture
- no admin / CRM workflow hints
- slow response pattern indicators
- no call-to-action structure

Output example:

- issue: No WhatsApp integration
- impact: Missed mobile inquiries
- severity: high
- estimated_loss: medium
- recommendation: WhatsApp bot + lead capture panel

### 3. AI Solution Recommendation Engine

Responsibilities:

- Convert scanner findings into software recommendations
- Map problems to solution bundles
- Generate personalized sales angles

Recommended outputs:

- CRM system
- booking system
- WhatsApp bot
- lead dashboard
- mobile app
- admin panel
- custom website upgrade

### 4. Instant Demo Generator

Responsibilities:

- Generate a quick demo landing page for each lead
- Use reusable templates by niche
- Personalize content with business name, niche, city, and pain points
- Produce shareable preview URLs

Template examples:

- clinic booking demo
- real estate lead dashboard demo
- school parent portal demo
- restaurant online ordering demo
- elevator service request portal demo

### 5. Outreach Automation

Responsibilities:

- Generate personalized outreach copy
- Queue and send email outreach
- Prepare WhatsApp outreach messages
- Prepare LinkedIn outreach messages
- Send events to n8n workflows

Channels:

- email
- WhatsApp
- LinkedIn

### 6. Lead Dashboard

Responsibilities:

- Track lead lifecycle
- View scanner results and demos
- Track outreach history
- Record meetings and closed deals

Lead statuses:

- discovered
- scanned
- contacted
- replied
- interested
- meeting_booked
- proposal_sent
- closed_won
- closed_lost

## Recommended Architecture

Use a monorepo with shared packages.

```text
mind-manage/
  apps/
    web/
      src/
        app/
          (auth)/
            login/
            register/
          dashboard/
            page.tsx
            discovery/
              page.tsx
            leads/
              page.tsx
              [leadId]/
                page.tsx
            scanner/
              page.tsx
            demos/
              page.tsx
              [demoId]/
                page.tsx
            outreach/
              page.tsx
            settings/
              page.tsx
          api/
            auth/
            health/
        components/
          dashboard/
          discovery/
          scanner/
          outreach/
          demos/
          ui/
        lib/
          api-client.ts
          auth.ts
          constants.ts
          validators.ts
        hooks/
        styles/
        types/
      public/
      middleware.ts
      next.config.ts
      package.json

    api/
      src/
        app.ts
        server.ts
        config/
          env.ts
          logger.ts
        routes/
          auth.routes.ts
          businesses.routes.ts
          scanner.routes.ts
          recommendations.routes.ts
          demos.routes.ts
          outreach.routes.ts
          leads.routes.ts
          uploads.routes.ts
          webhooks.routes.ts
        controllers/
          auth.controller.ts
          businesses.controller.ts
          scanner.controller.ts
          recommendations.controller.ts
          demos.controller.ts
          outreach.controller.ts
          leads.controller.ts
        services/
          business-discovery/
            google-maps.service.ts
            directories.service.ts
            lead-normalizer.service.ts
          scanner/
            website-fetcher.service.ts
            technology-detector.service.ts
            issue-detector.service.ts
            opportunity-score.service.ts
          ai/
            openai.service.ts
            recommendation-engine.service.ts
            outreach-writer.service.ts
            demo-copy.service.ts
          demos/
            demo-builder.service.ts
            template-renderer.service.ts
          outreach/
            email.service.ts
            whatsapp.service.ts
            linkedin.service.ts
            campaign-orchestrator.service.ts
          leads/
            lead-status.service.ts
            lead-activity.service.ts
          scraping/
            playwright-runner.ts
            website-audit.service.ts
        middlewares/
          auth.middleware.ts
          error.middleware.ts
          rate-limit.middleware.ts
          validation.middleware.ts
        jobs/
          rescan.job.ts
          outreach-followup.job.ts
        utils/
          urls.ts
          text.ts
          dates.ts
          scoring.ts
      package.json

  packages/
    db/
      prisma/
        schema.prisma
        migrations/
      src/
        client.ts
        seed.ts
      package.json

    ui/
      src/
        components/
        styles/
      package.json

    prompts/
      src/
        scanner-prompts.ts
        outreach-prompts.ts
        recommendation-prompts.ts
        demo-prompts.ts
      package.json

    types/
      src/
        business.ts
        lead.ts
        scanner.ts
        outreach.ts
        demo.ts
      package.json

  automation/
    n8n/
      workflows/
        lead-enrichment.json
        outreach-sequence.json
        meeting-followup.json
        rescan-trigger.json

  infrastructure/
    docker/
      Dockerfile.web
      Dockerfile.api
    compose/
      docker-compose.dev.yml
    nginx/
    scripts/
      bootstrap.sh
      bootstrap.ps1
      deploy.sh

  .env.example
  package.json
  turbo.json
  pnpm-workspace.yaml
  README.md
```

## Database Design

Recommended PostgreSQL tables:

### users

- id
- name
- email
- password_hash
- role
- created_at
- updated_at

### businesses

- id
- owner_user_id
- name
- niche
- city
- website
- phone
- email
- address
- source
- google_maps_url
- discovered_at
- created_at
- updated_at

### website_scans

- id
- business_id
- scanner_version
- homepage_url
- load_time_ms
- contact_form_found
- whatsapp_found
- booking_found
- crm_hint_found
- chatbot_found
- lead_capture_score
- response_score
- opportunity_score
- raw_html_snapshot_url
- created_at

### scan_issues

- id
- scan_id
- issue_type
- severity
- description
- revenue_loss_note
- recommendation_key
- created_at

### solution_recommendations

- id
- business_id
- scan_id
- title
- summary
- recommended_modules_json
- pricing_hint
- ai_reasoning
- created_at

### demo_templates

- id
- name
- niche
- slug
- template_config_json
- created_at

### demos

- id
- business_id
- recommendation_id
- template_id
- demo_url
- headline
- content_json
- screenshot_url
- created_at

### outreach_messages

- id
- business_id
- channel
- subject
- message_body
- personalization_json
- status
- created_at
- sent_at

### lead_pipeline

- id
- business_id
- current_status
- owner_user_id
- priority
- interest_score
- last_contacted_at
- next_follow_up_at
- created_at
- updated_at

### lead_activities

- id
- business_id
- lead_pipeline_id
- type
- notes
- metadata_json
- created_at

## API Surface

### Auth

- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/me

### Business Discovery

- GET /api/businesses
- POST /api/businesses/discover
- POST /api/businesses/import
- GET /api/businesses/:id
- PATCH /api/businesses/:id

### Website Scanner

- POST /api/scanner/run/:businessId
- GET /api/scanner/:businessId/latest
- GET /api/scanner/:scanId/issues

### Recommendation Engine

- POST /api/recommendations/generate/:businessId
- GET /api/recommendations/:businessId

### Demo Generator

- GET /api/demo-templates
- POST /api/demos/generate/:businessId
- GET /api/demos/:id

### Outreach

- POST /api/outreach/generate/:businessId
- POST /api/outreach/send/:messageId
- POST /api/outreach/send-batch

### Lead Dashboard

- GET /api/leads
- PATCH /api/leads/:id/status
- POST /api/leads/:id/activity
- GET /api/leads/metrics/summary

### Automation / Webhooks

- POST /api/webhooks/n8n/outreach-status
- POST /api/webhooks/n8n/meeting-booked

## UI Screens

### Dashboard

- KPIs: discovered, scanned, contacted, interested, meetings, closed
- recent businesses
- recent scans
- next follow-ups

### Discovery Page

- niche selector
- city selector
- source selector
- discover button
- business table

### Scanner Page

- selected business card
- scan summary
- problem list
- revenue loss warning
- scan screenshot preview

### Recommendation Page / Lead Detail

- detected issues
- recommended software stack
- pricing angle
- instant demo generate button
- outreach generate button

### Demo Page

- template selector
- preview pane
- publish/share URL

### Outreach Page

- channel tabs: email, WhatsApp, LinkedIn
- personalized message preview
- send now / queue later

### Leads Page

- kanban board or pipeline table
- filters by status, niche, city, owner
- business notes
- meeting scheduler

## Authentication

Recommended approach:

- NextAuth or custom JWT auth
- access token + refresh token
- protected dashboard routes
- role support for admin and sales users

Minimum auth rules:

- only authenticated users can access dashboards
- users can only access their own leads unless admin
- webhook endpoints secured with secret tokens

## AI Integration Plan

Use OpenAI for three focused jobs only:

### 1. Scanner explanation

Turn raw detected issues into business-language problem reports.

### 2. Recommendation generation

Map scan findings to solution packages.

### 3. Outreach personalization

Generate concise, niche-aware, business-specific sales outreach.

Guardrails:

- never let AI decide database writes directly
- store prompts and outputs for auditability
- cap tokens and cache repeat results per business scan

## Automation with n8n

Recommended workflows:

- new business discovered -> enrich lead
- scan complete -> generate recommendation
- recommendation ready -> create demo
- outreach approved -> send email / WhatsApp
- no response in 3 days -> schedule follow-up
- meeting booked -> update lead status

## Suggested Detection Strategy

Do not start with a heavy AI crawler first.

Start with deterministic checks:

- form tag detection
- WhatsApp link detection
- booking keywords
- chatbot widget scripts
- CRM widget scripts
- CTA count
- mobile contact buttons

Then layer AI summarization after deterministic scanning.

## Phased Implementation Plan

### Phase 1. Foundation

- bootstrap monorepo
- setup Next.js app
- setup Express API
- setup PostgreSQL + Prisma
- add auth
- add base dashboard shell

### Phase 2. Discovery

- business search form
- Google Maps integration
- lead normalization
- business table + detail page

### Phase 3. Scanner

- Playwright website fetcher
- deterministic issue detection
- scan report UI
- opportunity score

### Phase 4. Recommendations

- OpenAI recommendation service
- solution bundle generator
- pricing/value summary output

### Phase 5. Demo Generator

- demo templates by niche
- render demo landing pages
- store preview URLs

### Phase 6. Outreach

- generate channel-specific messages
- email integration
- WhatsApp click-to-send links
- LinkedIn copy-ready outreach panel
- n8n workflow handoff

### Phase 7. Lead Dashboard

- pipeline statuses
- activity log
- follow-up scheduling
- metrics dashboard

### Phase 8. Hardening

- rate limiting
- retry queues
- scan snapshots
- audit logging
- role permissions
- monitoring

## Recommended MVP Scope

If you want fast delivery, build only this first:

- auth
- business discovery by niche + city
- deterministic website scanner
- AI recommendation summary
- one reusable demo template
- email + WhatsApp outreach generation
- lead dashboard with statuses

Skip for MVP:

- full LinkedIn automation
- advanced CRM sync
- multi-user teams
- full visual page builder

## Important Constraints

### Google Maps API

- reliable but paid beyond free usage limits
- should cache results aggressively

### LinkedIn outreach

- safe support is message generation and copy assistance
- full automation is limited and risky

### WhatsApp outreach

- safe support is click-to-chat or approved Business API integrations

### Website scanning

- some sites block headless browsers
- add retries, timeouts, and screenshots for debugging

## Delivery Recommendation

Best implementation path:

- build this as a separate product or monorepo called Mind Manage
- keep the current FastAPI project isolated
- reuse only ideas and UI patterns, not the current server structure

## Next Build Option

If you want actual code scaffolding next, the best next task is:

1. create the monorepo structure
2. scaffold Next.js web app
3. scaffold Express API
4. add Prisma schema and initial migrations
5. add auth and dashboard shell
