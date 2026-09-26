# Member MCP Server Project

## Business Requirements

- An MVP of a Streamable HTTP based Member MCP Server web endpoint application for AI clients such as Claude Code CLI

## Technical Details

- Implement as a modern Python FastAPI, FastMCP MCP Server app for AI clients to use list of tools
- No persistence, Just 10 members with Name, email, mobile number
- No user management for the MVP
- Use popular libraries
- MCP tools: get_user_by_name, get_user_by_email, get_all_users
- Use uv for dependency/package management
- Use approprite folder names for source code files organization
- Project level venv
- Write boilerplate .gitignore
- write a start and stop service scripts for PC & Linux. Place these scripts in the scripts folder in the project root directory

## Strategy

1. Write plan with success criteria for each phase to be checked off. Include project scaffolding, including .gitignore, and rigorous unit testing.
2. Execute the plan ensuring all critiera are met
3. Carry out extensive unit testing, fixing defects
4. Only complete when the MVP is finished and tested, with the server running and ready for the user

## Coding standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever
