# Mind Manage

Mind Manage is a monorepo scaffold for a business discovery, website scanning, recommendation, demo generation, and outreach platform.

## Stack

- Next.js frontend
- Express API backend
- PostgreSQL + Prisma
- OpenAI integration hooks
- Playwright scanning hooks
- n8n automation workflow stubs

## Apps

- `apps/web`: dashboard UI
- `apps/api`: REST API
- `packages/db`: Prisma schema and client
- `packages/types`: shared types
- `automation/n8n`: workflow templates

The root scripts run the web and API workspaces directly through Corepack so they work even when `pnpm` is not globally installed.

## First Run

1. Use `corepack pnpm install` from `mind-manage`.
3. Copy `.env.example` to `.env`.
4. Start Postgres.
5. Run `corepack pnpm db:generate`.
6. Run `corepack pnpm db:migrate`.
7. Run `corepack pnpm dev`.

## MVP Modules Included In Scaffold

- business discovery dashboard
- website scanner report flow
- AI recommendation flow
- demo template flow
- outreach campaign flow
- lead pipeline shell

This scaffold is production-oriented but still requires dependency install, migrations, and provider credentials before it can run end to end.

## Deployment

Render is now the prepared deployment path for this monorepo.

1. Push the repository changes to GitHub.
2. In Render, create a new Blueprint and point it at `mind-manage/render.yaml`.
3. Let Render create the PostgreSQL database, API service, and web service.
4. After the first API deploy, confirm the actual API hostname and update `NEXT_PUBLIC_API_BASE_URL` in the `mind-manage-web` service if Render assigned a different URL than `https://mind-manage-api.onrender.com/api`.
5. Add real values for `OPENAI_API_KEY`, `GOOGLE_MAPS_API_KEY`, and `N8N_WEBHOOK_BASE_URL` in the API service if you want the live integrations enabled.

The local QA-validated flow covers discovery, scanning, recommendations, demos, outreach, and lead updates.
