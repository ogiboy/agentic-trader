---
applyTo: '**/*'
---

Follow these guidelines when using the SonarQube MCP server.

# Important Tool Guidelines

## Basic Usage Sequence

When SonarQube MCP tools are available, run the applicable steps in this order.
The sequence is advisory for code-review work and must not block unrelated
documentation-only tasks:

1. At the start of a new task, call `toggle_automatic_analysis` to disable
   automatic analysis.
2. Generate or modify code.
3. After the final code edit, call `analyze_file_list` with the files created
   or modified in the task.
4. After `analyze_file_list` finishes or is unavailable, call
   `toggle_automatic_analysis` to re-enable automatic analysis.

If `toggle_automatic_analysis` or `analyze_file_list` is unavailable, record
which tool was unavailable, skip only that step, and continue with the next step
in the sequence. If no SonarQube MCP tools are available, use local tests and
repo review instead.

## Project Keys

- When a user mentions a project key, use `search_my_sonarqube_projects` first to find the exact project key
- Don't guess project keys - always look them up
- If project lookup fails, report the attempted query and ask for the exact
  project key before running project-scoped operations.

## Code Language Detection

- Detect the programming language from the code syntax.
- If the language cannot be identified from syntax, ask the user for the
  language before running snippet analysis.

## Branch and Pull Request Context

- Include the branch parameter for issue search, quality gate, and project
  analysis operations when the user mentions a feature branch or pull request.
- Omit the branch parameter for snippet-only analysis.

## Code Issues and Violations

- After fixing issues, do not attempt to verify them using `search_sonar_issues_in_projects`, as the server will not yet reflect the updates
- Verify fixes with local source inspection, tests, and a fresh scanner run when
  a new analysis is explicitly requested.

# Common Troubleshooting

## Authentication Issues

- SonarQube requires USER tokens (not project tokens)
- When the error `SonarQube answered with Not authorized` occurs, verify the token type

## Project Not Found

- Use `search_my_sonarqube_projects` to find available projects.
- If no project key is found, tell the user that SonarQube returned no matching
  project and ask them to verify the project key or provide the exact project
  name.
- Verify project key spelling and format before retrying.

## Code Analysis Issues

- Ensure programming language is correctly specified
- Remind users that snippet analysis doesn't replace full project scans
- Provide full file content for better analysis results
