# VRC-groupinstance-notifer
Required Python, target group, target world, auth token.
when the target world isn't launched, it will be notify you via discord.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `config.json` file with your VRChat and Discord settings:

```json
{
    "GROUP_ID": "your_group_id",
    "TARGET_WORLD_ID": "your_world_id", 
    "DISCORD_WEBHOOK_URLS": {
        "LOG": "https://discord.com/api/webhooks/your_log_webhook",
        "INSTANCE": "https://discord.com/api/webhooks/your_instance_webhook",
        "STATS": "https://discord.com/api/webhooks/your_stats_webhook"
    },
    "USERNAME": "your_vrchat_username",
    "PASSWORD": "your_vrchat_password",
    "TOTP_SECRET": "your_2fa_secret",
    "MINIMUM_USERS": "3",
    "USER_AGENT": "your_user_agent"
}
```

## Testing

Run the test suite to verify everything is working correctly:

```bash
python3 -m unittest test_log.py -v
```

Or use the test runner:

```bash
python3 run_tests.py
```

The test suite includes 25 comprehensive tests covering:
- Log file parsing with various edge cases
- Hour-based analysis functionality  
- Discord notification handling
- Logging setup and configuration
- Cookie management
- Error handling and robustness 
