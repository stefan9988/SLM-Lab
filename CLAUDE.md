# Project Guidelines

## Package Manager

This project uses **uv** as its package manager.

## Branching

Always create a new branch before implementing a new feature.

## Clarification

If something is unclear about integration or requirements, ask questions before proceeding.

## Code Quality

Follow best coding principles: clean code, proper naming, separation of concerns, DRY, and SOLID.

## Testing

Write tests for all new features.

### Backend Tests

The backend uses **pytest**. Tests live in `tests/` with subdirectories mirroring the source: `tests/BE/` for backend and `tests/AI/` for AI modules. Shared fixtures (mock agent, FastAPI test client) are in `tests/conftest.py`.

- Run all backend tests: `uv run pytest`
- Run a specific test file: `uv run pytest tests/BE/test_app.py`
- Run a specific test: `uv run pytest tests/BE/test_app.py::test_name`

### Frontend Tests

The frontend uses **Vitest** with **React Testing Library**. Tests are co-located with components as `*.test.tsx` files in `FE/src/components/`.

- Run all frontend tests: `cd FE && npx vitest run`
- Run a specific test file: `cd FE && npx vitest run src/components/MyComponent.test.tsx`
- Run tests in watch mode: `cd FE && npx vitest`

## Environment Variables

When adding new environment variables, update `.env.example` accordingly.

## Formatting

When adding new code or making changes, run `uv run black .` to format the code.