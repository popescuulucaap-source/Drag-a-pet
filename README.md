# Drag a Pet Discord bot

Ready-to-add bot folder for the `Drag-a-pet` repository. It provides `/setup` and `/help`, per-rarity role configuration, and a small authenticated HTTP endpoint for the Roblox server to report each pet **when it actually spawns**.

## Add to your repo and host

1. Copy this entire folder into the GitHub repo.
2. In Fadehost, set the startup directory to this folder and install `requirements.txt`.
3. Set environment variables `DISCORD_TOKEN` and `API_KEY` (same API key will be set in the Roblox server script). Keep both private. Fadehost must expose the configured `PORT`.
4. Invite the bot with `bot` and `applications.commands` scopes, plus Send Messages and Use Slash Commands permissions. In the alert channel, allow the bot to mention the configured roles and `@everyone`.
5. Start the bot and run `/setup` in Discord. Select the channel; then select each rarity and the matching role. Roles are optional.

## Connect the Roblox game

The game has six wild zones; `ReplicatedStorage.PetConfig` defines each zone's pet weights. Its highest-income wild pet is **Sugar Dragon** (Divine, Candy zone, 1% weight). `ServerScriptService.DayNight` controls the in-game reset cycle. The bot deliberately does not guess a daily schedule: the game server must call this endpoint when a pet spawns.

POST JSON to `https://YOUR-FADEHOST-HOST/spawn` with header `Authorization: Bearer YOUR_API_KEY`:

```json
{"pet":"Sugar Dragon","rarity":"Divine","dayKey":"game-day-123"}
```

Send one request for every pet spawn. The bot sends the rarity role mention; if `pet` equals `Sugar Dragon`, it sends `@everyone **THE BEST PET SPAWNED**`. The game must have HTTP requests enabled, and its server script needs to make this POST on the server when its existing spawn code creates the pet. Do not put the API key in a LocalScript or expose it to players.

## Notes

- Guild settings are saved in `data/guilds.json`. Use persistent storage if Fadehost does not preserve the container filesystem on restart/redeploy.
- `@everyone` is enabled only for Sugar Dragon; ordinary role mentions are restricted to the configured role.
- Configure the bot's role above the notification roles it needs to mention.
