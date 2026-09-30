# Vercel agent-browser

**agent-browser** is a browser automation command-line tool built for AI agents. The agent drives a real Chrome browser: opening pages, clicking, filling forms, reading text and taking screenshots. It comes with a skill (a `SKILL.md` file) that teaches the agent how to use it.

It is from **Vercel Labs**, not Anthropic: https://github.com/vercel-labs/agent-browser. It works with Claude Code and other agents that support skills.

## How it works

It uses a snapshot-and-reference workflow. The agent never writes CSS or XPath selectors:

```bash
agent-browser open example.com
agent-browser snapshot -i            # interactive elements, each with a ref
#   button "Submit" [ref=e2]
#   textbox "Email" [ref=e3]
agent-browser fill @e3 "test@example.com"
agent-browser click @e2
agent-browser screenshot
```

- `snapshot` returns the page's accessibility tree, which is much smaller than the full HTML, with short refs like `@e2` for each element.
- The agent acts on those refs, then takes another snapshot to see the result.
- It is a native Rust CLI that talks to Chrome directly over the Chrome DevTools Protocol, without Playwright or Puppeteer.

## What it is used for

- Automating websites: navigating, clicking, filling forms, logging in
- Extracting data from web pages
- Testing web apps end to end and checking UI changes with screenshots
- Accessibility checks (it bundles axe-core)
- Running several isolated browser sessions in parallel

## Why use it instead of an MCP browser server

A skill plus a CLI is cheaper on context than an MCP browser server. The agent loads the skill instructions only when it needs them and runs short shell commands, instead of carrying many MCP tool definitions and large page dumps in context.

## Install

```bash
npm install -g agent-browser
agent-browser install     # downloads Chrome for Testing
```

For adding the skill to Claude Code, follow the repo README.

## What `npm install -g agent-browser` does

It installs the `agent-browser` command-line tool so it can be run from any terminal.

| Part | Meaning |
|---|---|
| `npm` | Node Package Manager, the installer that comes with Node.js (like `uv`/`pip` for Python) |
| `install` | Download a package from the npm registry (https://www.npmjs.com) and install it |
| `-g` | **Global**: install it for your whole user account instead of into the current project folder |
| `agent-browser` | The package name |

What happens when you run it:

1. npm downloads the `agent-browser` package and its dependencies from npmjs.com.
2. Because of `-g`, it goes into npm's global folder, not the project. On Windows that is usually `%APPDATA%\npm`.
3. npm creates an `agent-browser` command in that folder. The folder is on your PATH, so `agent-browser` works in any terminal, including the ones Claude Code uses.
4. The tool itself is a compiled Rust program. The npm package is mainly a way to deliver the right binary for your OS, so it does not need Node.js to do the browser work.

What it does not do:

- It does not download Chrome. That is the next command, `agent-browser install`.
- It does not change the project. Nothing is added to `pyproject.toml`, `package.json` or `.venv`.
- It does not install the skill into Claude Code. That is a separate step.

Requirements and cleanup:

- Node.js must be installed (check with `node -v` and `npm -v`).
- To uninstall it, run `npm uninstall -g agent-browser`.
- To install it only for one project instead, drop the `-g`. It then goes into that project's `node_modules/` and runs with `npx agent-browser`.

## Related options

- **`claude-in-chrome`**, a built-in Claude Code skill. It drives your existing, logged-in Chrome through the Claude extension.
- **Anthropic's own skills repo** (https://github.com/anthropics/skills) has a `webapp-testing` skill based on Playwright.

## Use case: verifying a React / Next.js UI built with Claude Code

The main use case is letting Claude Code check its own UI work in a real browser. Without a browser, Claude Code writes React/Next.js code but can only run the build and unit tests; it never sees the page. With agent-browser, it can open the running app, click through it, find bugs and fix them in the same session.

### Example: adding a "Member Directory" page

A Next.js app gets a new page that lists members and has a search box.

**1. Start the dev server** (in a separate terminal, or ask Claude Code to start it in the background):

```bash
npm run dev        # http://localhost:3000
```

**2. Give Claude Code a prompt that includes verification:**

```
Add a /members page that lists members in a table with a search box
that filters by name or email. When done, use agent-browser to open
http://localhost:3000/members, test the search, check the browser
console for errors, take a screenshot, and fix any problems you find.
```

**3. What Claude Code then does on its own:**

```bash
agent-browser open http://localhost:3000/members
agent-browser snapshot -i
#   textbox "Search members" [ref=e4]
#   table ... 10 rows
agent-browser fill @e4 "alice"
agent-browser snapshot -i           # confirms only 1 row remains
agent-browser screenshot            # checks the layout visually
```

If something is wrong, it goes back to the code, fixes it, reloads the page and checks again. Examples: the table does not filter, the page throws a hydration error, or the search box is missing a label.

This works with `localhost:3000` because agent-browser runs on your PC, the same as Claude Code. It is the same local-client rule as in `How_MCP_Works.md`.

### Other uses in a React/Next.js project

| Use case | Example prompt |
|---|---|
| **Test a form flow** | "Fill the signup form with valid and invalid data and verify the validation messages appear" |
| **Reproduce a bug** | "Open /checkout, add two items, click Pay, and tell me why the total is wrong" |
| **Check a responsive layout** | "Screenshot the home page at mobile and desktop widths and fix any overflow" |
| **Check accessibility** | "Run an accessibility check on /members and fix missing labels and contrast issues" |
| **Smoke test after a refactor** | "Visit every page in the app/ directory and report any that error or render blank" |
| **Test a login flow** | "Log in with the test user, then verify the dashboard shows the user's name" |
| **Turn a session into tests** | "After you verify the flow manually, write a Playwright test that covers it" |

The last row works well together with the others. agent-browser is good for exploring and checking during development, and Playwright tests keep the checks running in CI afterwards.

### Make it automatic

Add a short rule to the project's `CLAUDE.md`:

```markdown
## UI verification
After any UI change, use agent-browser against http://localhost:3000
to verify the change works, check for console errors, and take a
screenshot. Fix issues before reporting the task as done.
```

### Tips

- **Use test data only.** Point it at a local or staging environment, not production accounts.
- **Keep the dev server running.** Next.js hot reload lets Claude Code fix the code and re-check immediately without restarting.
- **Ask for evidence.** Asking for a screenshot or snapshot output in the final report shows what Claude Code actually checked.

## Using the Chrome already installed on your PC

Downloading a separate Chrome is only agent-browser's default. It can use your installed Chrome, and Claude Code also has a built-in way to use your real browser.

### Why the default is a separate Chrome

`agent-browser install` downloads **Chrome for Testing**, a build Google publishes for automation. Tools default to it because:

| Reason | Explanation |
|---|---|
| **Safety** | Your everyday Chrome is logged into email, banking and work accounts. A separate browser means an agent cannot act as you on those sites by accident. |
| **Isolation** | Your open tabs, extensions and cookies do not interfere with tests, and tests do not mess up your browsing. |
| **Predictable version** | Your Chrome auto-updates. A pinned version behaves the same on every run and on every machine, including CI. |
| **Chrome's own restrictions** | Newer Chrome versions (136+) block automation through remote debugging on your **default** profile, to stop malware from stealing your logins. |

### Option 1: Use your installed Chrome with agent-browser

```bash
agent-browser --executable-path "C:\Program Files\Google\Chrome\Application\chrome.exe" open http://localhost:3000
```

Or set it once as an environment variable:

```powershell
$env:AGENT_BROWSER_EXECUTABLE_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

This uses your Chrome program, but still with a separate, clean profile. You can then skip `agent-browser install`.

### Option 2: Connect to a Chrome window you started

Start Chrome with remote debugging and a separate profile folder, then connect to it:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-agent-profile"
```

```bash
agent-browser connect 9222
```

You watch the browser window while Claude Code drives it. You can log in to your app manually once, and the logins are kept in that profile folder for later sessions. agent-browser also has `--auto-connect` to find a running Chrome, and `--profile` to reuse a saved login profile.

### Option 3: Use your real, logged-in Chrome (built into Claude Code)

Claude Code's built-in **`claude-in-chrome`** skill works through the **Claude in Chrome extension** installed in your normal Chrome:

- It uses your existing browser, tabs and logins.
- It opens its own tabs and asks for permission per site before acting.
- Setup: install the Claude in Chrome extension, then ask Claude Code something like "use Chrome to open http://localhost:3000 and test the search box".

### Which to use

| Situation | Best choice |
|---|---|
| Testing a Next.js app on localhost | agent-browser with Chrome for Testing or Option 1 (clean, repeatable) |
| Watching the agent work, or logging in by hand once | Option 2 |
| Tasks that need your real accounts or sessions | `claude-in-chrome` (Option 3) |
| CI / automated tests | Chrome for Testing or Playwright (pinned version) |

Be careful with your main profile. Anything the agent can reach in that browser, it can act on as you. For development testing, a separate profile is the safer default.

## agent-browser vs Playwright

They solve different problems, even though both control Chrome. **Playwright** is a test automation framework: you (or Claude Code) write test code that runs the same way every time, e.g. in CI. **agent-browser** is a command-line tool that lets an AI agent drive a browser step by step while it works.

### Side-by-side

| | agent-browser (Vercel) | Playwright (Microsoft) |
|---|---|---|
| **Main purpose** | Let an AI agent explore and operate a browser live | Automated end-to-end tests and scripted automation |
| **Who drives it** | The LLM decides each step at runtime | Pre-written code runs deterministically |
| **Interface** | Shell commands (`open`, `snapshot`, `click @e2`) | Code APIs (TypeScript/JS, Python, Java, .NET) plus a test runner |
| **Finding elements** | Refs from an accessibility snapshot (`@e2`) | Locators in code (`getByRole`, `getByText`, CSS) |
| **Browsers** | Chrome/Chromium only (via CDP) | Chromium, Firefox and WebKit (Safari engine) |
| **Built with** | Native Rust binary | Node.js core with bindings for other languages |
| **Repeatability** | Varies; the agent may take different steps each run | High; the same steps every run |
| **CI/CD** | Not its purpose | Built for it: parallel runs, retries, sharding, HTML reports, traces, video |
| **Assertions** | The agent judges the result by reading the page | Built-in `expect` with auto-waiting |
| **Cost per run** | LLM tokens every time | Free once the test is written |
| **Maturity** | New (2025/2026) | Mature, widely used, large ecosystem |

### Where Playwright MCP fits

**Playwright MCP** (`@playwright/mcp`) is Microsoft's MCP server that gives agents browser tools backed by Playwright. It is the direct competitor to agent-browser:

| | agent-browser | Playwright MCP |
|---|---|---|
| How the agent uses it | Skill + shell commands | MCP tools |
| Context cost | Lower: the skill loads on demand and output is short | Higher: tool definitions are always in context and page snapshots can be large |
| Browsers | Chrome only | Chromium, Firefox, WebKit |
| Setup in Claude Code | Install CLI + skill | `claude mcp add playwright -- npx @playwright/mcp@latest` |

### Which to use for a React/Next.js app

Use them together; they cover different stages:

```
Develop           ->  agent-browser (or Playwright MCP)
                      Claude Code builds a feature, checks it in a browser,
                      fixes bugs as it goes

Lock it in        ->  Playwright tests
                      Claude Code writes tests for the checked flow

Every commit / PR ->  Playwright in CI
                      Runs fast and free, catches regressions
```

| If you need... | Use |
|---|---|
| Claude Code to check its own UI changes while coding | agent-browser |
| Regression tests on every commit | Playwright |
| Testing in Safari/Firefox | Playwright |
| Exploratory testing or reproducing a reported bug | agent-browser |
| Lowest context/token use for agent browsing | agent-browser |
| Standard MCP tooling that works across many agent clients | Playwright MCP |

In short: agent-browser is for **the agent checking work during development**, and Playwright is for **tests that run the same way on every build**. A good prompt connects the two: "verify the flow with agent-browser, then write a Playwright test for it."

The token-efficiency claims come from the agent-browser README, so check them against your own usage.

## Sources

- [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser)
- [agent-browser core SKILL.md](https://github.com/vercel-labs/agent-browser/blob/main/skill-data/core/SKILL.md)
- [Agent Browser on mcpservers.org](https://mcpservers.org/agent-skills/vercel/agent-browser)
