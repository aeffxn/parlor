# 🎮 Parlor

![Python](https://img.shields.io/badge/Python-3.10%2B-yellow?style=flat-square&logo=python&logoColor=black)
![UI](https://img.shields.io/badge/UI-HTML%20%2B%20CSS-black?style=flat-square)
![Multiplayer](https://img.shields.io/badge/Multiplayer-LAN-orange?style=flat-square)
![Status](https://img.shields.io/badge/Status-Playable%20first%20edition-8be0a0?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-black?style=flat-square)

Parlor turns the laptop in the middle of the room into a tiny arcade. Friends join from a phone browser, pick up a controller, and get competitive. Five quick games, one local room, and no account, app install, or cloud service in the way.

> Made for the friends who say “one more round” and mean it.

## 📑 In this room

- [Games included](#-games-included)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Running a game night](#-running-a-game-night)
- [Project structure](#-project-structure)
- [How it works](#-how-it-works)
- [The theme](#-the-theme)
- [Network and security](#-network-and-security)
- [Testing](#-testing)
- [Adding a game](#-adding-a-game)
- [Planned / coming soon](#-planned--coming-soon)
- [Roadmap](#-roadmap)
- [License and contributing](#-license-and-contributing)

## 🎮 Games included

| Game | What happens |
|---|---|
| ⚡ **Quickdraw** | A randomized signal, false starts, reaction times, and three rounds of score chasing. |
| 🧠 **Quiz Show** | Original offline trivia questions, a 16-second clock, and a speed bonus for correct answers. |
| 🔤 **Word Rush** | Unscramble a word from its hint. The first correct guess scores once per player. |
| 🎨 **Color Clash** | Take turns claiming a 6×6 board. The room gets 24 claims; tile ownership decides the territory score. |
| ☄️ **Meteor Run** | Dodge falling hazards with left and right phone buttons. The last runner standing, or the longest survivor, takes it. |
| ✊ **Rock Paper Scissors** | Pick in secret, reveal together, and score for each opponent you beat. |
| # **Closest Wins** | Guess a hidden number from 1 to 100; closest guesses share the points. |
| ☝ **Hot Take** | Take a side on a room-ready opinion; the minority gets the points. |
| ≡ **List Blitz** | Name up to three things that fit a category. Original answers score. |
| ↗ **Memory Mix** | Watch the host screen’s arrow pattern and repeat it on your phone. |

Each game has a rules and ready screen, an active round, server-owned scoring, and a results screen. Quiz Show and Word Rush run three rounds; the others run one. Use **Next round**, **Restart**, or **Lobby** to keep the night moving.

## 🛠 Requirements

- Python 3.10 or newer on the host computer.
- A browser with JavaScript enabled on host and player devices. The controller includes fallbacks for older Safari versions, including iOS 9; the iPad mini 1 has not been physically device-tested.
- All devices connected to the same trusted Wi-Fi network.
- No Python, app install, account, API key, or package install on joining devices.

Parlor uses only the Python standard library. `requirements.txt` is intentionally empty of third-party packages.

## 📦 Installation

Download or clone this repository, then open a terminal in the `Parlor` folder:

```bash
python --version
python server.py
```

On Windows, double-click `Start-Parlor.bat`. If `python` is not on PATH, install Python 3.10+ and enable the PATH option during setup.

The first run does not create files or ask for setup. The host page opens at `http://localhost:8765` (paste that address into a browser if it does not open automatically). Change the port with `python server.py --port 9000`.

## 🚀 Running a game night

1. Start Parlor on the computer connected to the room’s Wi-Fi.
2. Open the host screen at `http://localhost:8765`.
3. Share the LAN address shown on screen, or the address printed in the terminal. Friends open its `/controller.html` page on their own devices.
4. Enter the four-character room code and a display name. Duplicate names get a small number suffix.
5. Choose a game on the host screen. Everyone taps **I’m ready** on their own phone.
6. Pick the next round, restart, or head back to the lobby when the results are in.

Parlor supports up to eight active players. A disconnected player can refresh and rejoin with the saved browser session; stale sessions are removed after 90 seconds.

The host can choose a shared room theme from the host screen or any joined controller. Open **Host controls** on a phone to select and start games, advance or restart rounds, or return to the lobby. These controls affect the shared game session; they do not control the host computer itself.

## 📂 Project structure

```text
Parlor/
├── server.py                 # Local HTTP server, room API, and host authentication
├── parlor/games/catalog.py   # Five server-authoritative game rules and content
├── web/host.html             # Shared-screen host layout
├── web/host.js               # Host lobby, shared theme, and game-night actions
├── web/controller.html       # Mobile-first join and controller layout
├── web/controller.js         # Player session, game controls, and remote host panel
├── web/compat.js             # Fetch and browser API fallbacks for older Safari
├── web/style.css             # Shared visual system and responsive layouts
├── tests/test_parlor.py      # Room, lifecycle, and game rule tests
├── Start-Parlor.bat          # Windows launcher
├── requirements.txt          # No external packages required
└── README.md
```

## ⚙️ How it works

The Python host binds to the local network and serves the static browser screens plus a small JSON API. The host screen receives a random management key at page load; the LAN join page never receives that key. Player sessions use random, unguessable browser tokens stored locally in that browser.

Browsers poll the local server several times per second for room and game state. Controller actions are short HTTP requests. This keeps the code dependency-free and works through ordinary browsers, with a little more update delay than a WebSocket implementation. The server checks every action, owns all scores, limits the room to eight players, and drops inactive sessions. Game rules live apart from request handling in `parlor/games/catalog.py`.

## 🎨 The theme

Parlor uses charcoal cabinet-like panels, warm paper-white text, and a punchy yellow signal color. Each game gets a small accent color and its own visual cue, while the typography and spacing keep the host board readable from across a room. The controller is built around big thumb-sized buttons, a quick join form, and layouts that fit narrow phone screens. Reduced-motion preferences and keyboard focus outlines are respected.

The UI uses system fonts and does not require remote fonts or art. Older Safari uses XMLHttpRequest for API calls and flexbox layout where CSS Grid is unavailable.

## 🔒 Network and security

Parlor is intended for a private, trusted local network. The server binds to all network interfaces so nearby devices can connect. It does not configure port forwarding, use a cloud relay, or require an external service. Keep the terminal open while hosting and stop it with `Ctrl+C` when finished.

Traffic uses plain HTTP, with no TLS. Anyone who can reach the host on the local network may be able to observe or interfere with game traffic. Do not host on public Wi-Fi or an untrusted network. The game is for a friendly LAN, not a hardened public server. A firewall may ask whether Python should be allowed on a private network; allow it only on the trusted network you intend to use.

The LAN address is discovered from the host’s active network route. If the system has no active route, Parlor falls back to `127.0.0.1`, which only works on the host itself; use the address printed by your operating system’s network settings in that case.

## 🧪 Testing

Run the automated suite with Python’s built-in test runner:

```bash
python -m unittest discover -s tests -v
```

It covers room codes, invalid names, unique names, the eight-player cap, reconnection, stale cleanup, host game transitions, unauthorized player actions, and scoring/round behavior for each game.

## ➕ Adding a game

Add a game’s display name, description, and player-facing rules to `GAMES` in `parlor/games/catalog.py`. Add its round setup, validated actions, timer or end condition, and public display state to the `Game` class. Then add its host board in `activeMarkup()` in `web/host.js` and its touch controls in `render()` in `web/controller.js`. Keep scores and the decision about whether an input is valid on the server. Add tests beside the existing `GameTests` before listing the game in the UI.

## 🚧 Planned / coming soon

- A printable one-page party setup card with the local address and room code.
- Optional sound effects that can be muted from the host screen.
- A small custom question pack format for making your own trivia rounds.

## 🗺️ Roadmap

- [x] Host and phone controller screens
- [x] Room codes, reconnectable player sessions, and an eight-player lobby
- [x] Five playable server-authoritative games
- [x] Local question and word banks
- [x] Automated room and game tests
- [x] Offline-friendly, dependency-free Python host
- [ ] QR code join card for the local controller address
- [ ] Importable custom trivia packs
- [ ] Optional sound toggle and more party-ready polish

## 📄 License and contributing

Parlor is released under the [MIT License](LICENSE). Issues and small pull requests are welcome. Keep the server understandable, avoid adding mandatory cloud services, and include tests when changing game rules.
