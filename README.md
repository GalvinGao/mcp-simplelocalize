# `mcp-simplelocalize`

A MCP (Model Context Protocol) server implementation for [SimpleLocalize](https://simplelocalize.io).

## Usage

### Install

1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository

```bash
git clone https://github.com/GalvinGao/mcp-simplelocalize.git
```

3. Install dependencies

```bash
uv sync
```

4. Configure Cursor

You may wish to put this at `.cursor/mcp.json` under your project root, since SimpleLocalize API Key is specific to a single project.

Don't forget to add it to your `.gitignore` file to avoid exposing your API key.

```json
{
	"mcpServers": {
		"simplelocalize": {
			"command": "uv",
			"args": [
				"run",
				"--project",
				"/path/to/mcp-simplelocalize/",
				"/path/to/mcp-simplelocalize/main.py"
			],
			"env": {
				"SIMPLELOCALIZE_API_KEY": "your-api-key-here"
			}
		}
	}
}
```

5. Describe your project localization requirements under `.cursorrules`. For example:

```markdown
## Translations
- Put all translations under the `default` namespace
- Language codes supported by this project: `en-US`, `ja-JP`, `ko-KR`, and `zh-Hant`.
- (any other conventions you want the LLM to follow, e.g. key naming style, etc. or just give it some examples would work well)
```

6. Done! Enjoy prompting something like "Localize this component and update it to SimpleLocalize".

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.
