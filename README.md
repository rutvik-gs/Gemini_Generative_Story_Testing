# Gemini_Generative_Story_Testing
## Requirements
-   Clone this repository
-   First install `uv` python package manager
-   Make sure your python version is `3.12`

## How to run this project ?
-   Export your Gemini API key first. Run `export GEMINI_API_KEY={Your API Key Goes here}`
    -   For Windows `Set-Item -Path Env:GEMINI_API_KEY -Value "{Your API Key Goes here}"`
-   Run `uv sync`
-   Once all packages are resolved run `uv run python src/main.py`