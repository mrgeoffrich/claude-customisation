---
name: nextjs-starter
description: Scaffold a new full-stack Next.js application with shadcn/ui components, Tailwind CSS v4, Prisma ORM, dark mode theming, and a polished landing page. Use this skill whenever the user wants to start a new project, create a new app, bootstrap a Next.js application, set up a full-stack starter, or mentions wanting shadcn + Prisma + Next.js together. Also trigger when someone says "new app", "start a project", "bootstrap", "scaffold", or "create a starter" in the context of web development.
allowed-tools: Bash, Write, Edit, Read, Glob, Grep, AskUserQuestion
---

# Create a New Full-Stack Next.js Application

Scaffold a production-ready Next.js app with shadcn/ui, Tailwind v4, Prisma, and dark mode — everything wired together and working out of the box.

## Gather project details

Before doing anything, ask the user for these details (suggest the defaults shown):

1. **Project name** — kebab-case, e.g. `my-app`
2. **Database provider** — `sqlite` (default, great for local dev), `postgresql`, or `mysql`
3. **Base color theme** — one of the shadcn base colors:
   - `neutral` (default) — clean, modern
   - `zinc` — cool-toned
   - `stone` — warm
   - `slate` — blue-tinted
   - `gray` — classic
4. **Starter components** — suggest: `button card input label dialog dropdown-menu sheet separator avatar badge`

Wait for confirmation before proceeding.

## Stack overview

Understanding what each piece does helps you make good decisions if something unexpected comes up:

- **Next.js** (App Router, TypeScript, Turbopack) — the framework. `create-next-app` handles the initial scaffolding. Note: the CLI will ask interactive questions about React Compiler and AGENTS.md — answer yes/no based on preference, or pipe defaults to skip them.
- **shadcn/ui** — not a component library you install, but a CLI that copies well-built components into your project. `npx shadcn@latest init --defaults` sets up the config, CSS variables, and `cn()` utility. Then `npx shadcn@latest add <components>` copies in what you need.
- **Tailwind CSS v4** — comes with `create-next-app`. Uses CSS-first configuration with `@theme` directives instead of `tailwind.config.js`. shadcn's init handles the integration.
- **Prisma v7** — the ORM. Major differences from earlier versions: uses `prisma-client` provider (not `prisma-client-js`), generates client to `src/generated/prisma/`, requires driver adapters (`@prisma/adapter-libsql` for SQLite, `@prisma/adapter-pg` for PostgreSQL), and creates a `prisma.config.ts` file for datasource configuration. Needs a singleton pattern in Next.js because hot-reload creates new module instances, which would exhaust the connection pool without it.
- **next-themes** — handles dark mode. Must be installed explicitly (`npm install next-themes`) — it is NOT auto-installed by `shadcn init`. Needs a client-component wrapper (`ThemeProvider`) in the root layout.

## Build sequence

### 1. Create the Next.js app

```bash
npx create-next-app@latest <project-name> --typescript --tailwind --eslint --app --src-dir --turbopack --import-alias "@/*"
```

The CLI may prompt interactively for React Compiler (say no for a simpler start) and AGENTS.md (say yes). If running non-interactively, pipe answers: `echo "no\nyes" | npx create-next-app@latest ...` or just handle the prompts as they come.

`cd` into the project directory for everything that follows.

### 2. Initialize shadcn/ui

If the user chose the default `neutral` base color:
```bash
npx shadcn@latest init --defaults
```

If the user chose a different base color (e.g. zinc, stone, slate, gray), use the `--preset` flag to apply it automatically — this sets the correct CSS variables in `globals.css` without manual editing:
```bash
npx shadcn@latest init --preset "https://ui.shadcn.com/init?baseColor=zinc"
```

Replace `zinc` with the user's chosen color. This is much faster than initializing with defaults and then manually replacing all the oklch CSS variables.

This creates `components.json`, `src/lib/utils.ts` (the `cn()` helper), and wires up CSS variables in `globals.css`.

Then install `next-themes` explicitly — it is not included by `shadcn init`:
```bash
npm install next-themes
```

### 3. Add starter components

```bash
npx shadcn@latest add button card input label dialog dropdown-menu sheet separator avatar badge
```

Adjust based on what the user chose in step 1.

### 4. Set up dark mode

Dark mode needs three pieces. The reason `next-themes` requires a wrapper component is that it uses React context, which must be a client component — but the root layout is a server component.

**a) ThemeProvider** — Copy `assets/theme-provider.tsx` from the skill directory to `src/components/theme-provider.tsx`. Read the asset file and write it to the project.

**b) ThemeToggle** — Copy `assets/theme-toggle.tsx` to `src/components/theme-toggle.tsx`. This gives users a sun/moon toggle button built with shadcn's Button component.

**c) Wire into the root layout** — Edit `src/app/layout.tsx`:
- Add `suppressHydrationWarning` to the `<html>` tag (next-themes modifies this element and React will warn without it)
- Wrap `{children}` with the ThemeProvider:

```tsx
<ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
  {children}
</ThemeProvider>
```

The `attribute="class"` is important — Tailwind's dark mode uses the `dark` class on `<html>`.

### 5. Install and configure Prisma

Prisma v7 has significant changes from earlier versions. Follow these steps carefully.

**a) Install Prisma and the driver adapter for the chosen database:**

For SQLite:
```bash
npm install prisma && npm install @prisma/adapter-libsql @libsql/client
```

For PostgreSQL:
```bash
npm install prisma && npm install @prisma/adapter-pg pg
```

**b) Initialize** with the user's chosen provider:
```bash
npx prisma init --datasource-provider sqlite
```
(or `postgresql` / `mysql`)

This creates:
- `prisma/schema.prisma` — with `provider = "prisma-client"` and `output = "../src/generated/prisma"`
- `prisma.config.ts` — datasource URL configuration (reads `DATABASE_URL` from `.env`)
- `.env` — with `DATABASE_URL`

**c) Set up the singleton** — Copy the appropriate asset template to `src/lib/db.ts`:
- For SQLite: use `assets/db-sqlite.ts`
- For PostgreSQL: use `assets/db-postgresql.ts`

Read the asset file from the skill directory and write it to the project.

The singleton matters because Next.js hot-reload in development creates fresh module instances on every save. Without it, each reload spawns a new `PrismaClient` with its own connection pool, and you quickly hit database connection limits. The driver adapter (`PrismaLibSql` or `PrismaPg`) is required by Prisma v7 — the zero-argument `new PrismaClient()` constructor no longer works.

**d) Add a starter model** to `prisma/schema.prisma` — append after the existing generated content:

```prisma
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
```

**e) Generate the Prisma client and run the initial migration:**
```bash
npx prisma generate
npx prisma migrate dev --name init
```

Run `prisma generate` first — this creates the TypeScript client in `src/generated/prisma/` that your code imports. The migration also runs generate, but if migration fails (e.g. no database server for PostgreSQL), you still need the generated client for the build to succeed.

**f) Add `postinstall` to `package.json`** — this ensures `prisma generate` runs on `npm install`, which is required for deployment (e.g. Vercel):
```json
"postinstall": "prisma generate"
```

### 6. Secure environment files

Verify `.gitignore` includes:
```
.env
*.db
*.db-journal
```

The `.env` is created by `prisma init` and contains `DATABASE_URL`. The `.db` entries matter for SQLite.

### 7. Create a landing page

Replace `src/app/page.tsx` with a clean starter that:
- Uses shadcn components (Card, Button at minimum)
- Shows the ThemeToggle in the top-right
- Has a centered hero with the project name and a "Get Started" button
- Looks good in both light and dark mode
- Is responsive

Keep it minimal and professional. Use Tailwind v4 utility classes.

### 8. Verify

Run `npm run dev` and check for build errors. Fix anything that comes up — the dev server should start cleanly with Turbopack.

## Wrap up

Give the user a concise summary:

- **Project location** and how to start it (`npm run dev`)
- **Database**: provider and location/URL
- **Theme**: base color + dark mode via system preference
- **Installed components**: list
- **Key files**: `src/lib/db.ts`, `src/components/theme-provider.tsx`, `src/components/theme-toggle.tsx`, `prisma/schema.prisma`, `components.json`

And remind them of the workflows they'll use most:
- Add models: edit `prisma/schema.prisma`, then `npx prisma migrate dev --name <description>`
- Add components: `npx shadcn@latest add <component-name>`
- Browse components: https://ui.shadcn.com/docs/components
- Browse themes: https://ui.shadcn.com/themes
