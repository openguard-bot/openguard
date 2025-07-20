## Brief overview
This document outlines project-specific guidelines for developing the OpenGuard application, covering its multi-faceted architecture and preferred development practices.

## Project Structure
- The project is composed of a Python backend (Discord bot and FastAPI dashboard API), a React/Vite frontend dashboard, and an Astro-based website.
- Backend code resides primarily in the root directory (`bot.py`, `cogs/`, `database/`) and `dashboard/backend/`.
- Frontend code for the dashboard is in `dashboard/frontend/`.
- The public-facing website is located in `website/`.
- Configuration files are found in `configs/`.
- Utility scripts are in `scripts/`.
- The project uses yarn, with workspaces for the frontend and website.

## Backend Development (Python)
- **Frameworks**: Utilize `discord.py` for bot functionality and `FastAPI` for the dashboard API.
- **Dependency Management**: `requirements.txt` for Python dependencies.
- **Database Interaction**: Use the `database/` module for all database operations, preferring `SQLAlchemy` ORM patterns where applicable.
- **Modularity**: Organize bot features into cogs within the `cogs/` directory.
- **API Design**: Follow RESTful principles for the FastAPI endpoints.

## Frontend Development (React, Astro)
- **Dashboard**: Developed with React and Vite, using `Tailwind CSS` for styling and `Shadcn UI` components (evident from `dashboard/frontend/src/components/ui/`).
- **Website**: Built with Astro, leveraging its component-based architecture.
- **Styling**: Prefer `Tailwind CSS` for utility-first styling.
- **Component Reusability**: Design UI components to be reusable across the dashboard.
- **State Management**: Implement clear patterns for state management within React components.

## Database Management (PostgreSQL)
- **ORM**: Prefer `SQLAlchemy` for interacting with the PostgreSQL database.
- **Migrations**: Manage database schema changes using SQL migration scripts located in `database/migrations/`.
- **Connection**: Ensure secure and efficient database connections via `database/connection.py`.

## General Coding Practices
- **Naming Conventions**: Follow standard Python (snake_case for variables/functions, PascalCase for classes) and JavaScript/TypeScript (camelCase for variables/functions, PascalCase for components/classes) naming conventions.
- **Code Readability**: Prioritize clear, concise, and well-commented code.
- **Error Handling**: Implement robust error handling mechanisms in both backend and frontend.
- **Testing**: Write unit and integration tests for critical components (e.g., `dashboard/backend/tests/`, `dashboard/frontend/src/components/`).

## Communication Style
- **Conciseness**: Responses should be direct and to the point, avoiding conversational filler.
- **Technical Detail**: Provide sufficient technical detail when explaining code changes, architectural decisions, or debugging steps.
- **Tool Usage**: Clearly state which tool is being used and why, especially for complex operations.