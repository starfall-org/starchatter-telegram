# Starchatter Telegram Bot

A Telegram bot built with Python, featuring AI integrations, database support, and various handlers for commands and events.

## Features

- AI-powered chatbot with support for multiple providers
- Poem generation
- Image handling
- Group and channel management
- Database integration (local and cloud)
- Admin controls and system commands

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/starfall-org/starchatter-telegram.git
   cd starchatter-telegram
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your configuration in `app/config.py`

4. Run the bot:
   ```bash
   python -m app
   ```

## Docker

You can also run the bot using Docker:

```bash
docker build -t starchatter-telegram .
docker run starchatter-telegram
```

## Usage

- Add the bot to your Telegram group or channel
- Use commands like `/chat`, `/poem`, `/image`, etc.
- Configure AI providers and models through admin commands

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
