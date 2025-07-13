# OpenGuard

OpenGuard is a modular and extensible Discord moderation bot, designed to automate server management, enforce community rules, and protect members from abuse and spam. Written in Python and licensed under GPL-3.0, OpenGuard integrates seamlessly into Discord servers and provides customizable features for a wide range of moderation needs.

## Features

- **Automated Moderation:** Detects spam, abusive language, and unwanted behaviors with configurable triggers.
- **Customizable Rules:** Define server-specific moderation policies using YAML or JSON configuration.
- **Logging & Auditing:** Tracks moderation actions and provides audit logs for server administrators.
- **Role Management:** Manages user roles and permissions in response to infractions or server events.
- **Extensible Plugins:** Add or remove features via a clean plugin architecture for future-proof customization.
- **Notifications:** Sends alerts to moderators and users for rule violations, warnings, and bans.
- **Multi-language Support:** Adapt moderation messages for international communities.

## Setup

### Prerequisites

- Python 3.8 or newer
- Discord bot token ([Create a bot](https://discord.com/developers/applications))

### Installation

Clone the repository:
```sh
git clone https://github.com/discordOpenGuard/OpenGuard.git
cd OpenGuard
```

Install dependencies:
```sh
pip install -r requirements.txt
```

### Configuration

1. Copy the sample configuration:
    ```sh
    cp config.example.yaml config.yaml
    ```
2. Edit `config.yaml` to add your Discord bot token and server-specific settings.

### Running the Bot

```sh
python main.py
```

## Usage

Once started, OpenGuard will join your Discord server and begin monitoring activity according to your configuration.

- Use `!help` in Discord to view available commands.
- Moderators can adjust rules and actions via the configuration file or bot commands (if enabled).
- Audit logs are stored in the `logs/` directory.

## Contributing

Contributions are welcome! Please fork the repo, create a feature branch, and submit a pull request.

- Follow PEP8 style guidelines.
- Add tests for any new features.
- Ensure that no sensitive information (e.g., bot tokens) is committed.

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.

## Links

- [GitHub Repo](https://github.com/discordaimod/openguard)
- [Discord Support Server](https://discord.gg/SBCzKepBWF)
- [OpenGuard site](https://openguard.lol)
- [Discord Developer Portal](https://discord.com/developers/applications)
