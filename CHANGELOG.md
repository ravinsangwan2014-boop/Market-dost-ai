# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-09-16

### Added
- **Webhook Callback System**: Register, manage, and trigger webhooks for price/P&L/score changes
- **Callback Management Endpoints**: `/callbacks/register`, `/callbacks/unregister`, `/callbacks/list`, `/callbacks/history`
- **Enhanced Error Handling**: Comprehensive try-catch blocks with logging
- **Structured Logging**: INFO/WARNING/ERROR level logs for debugging
- **Docker Compose**: Multi-service orchestration (API + Worker)
- **Configuration Template**: `.env.example` for easy setup
- **Comprehensive Tests**: Unit tests for all endpoints
- **Production Documentation**: Detailed README with examples
- **Type Hints**: Python type annotations for better code quality
- **Non-blocking Callbacks**: Async callback triggers don't block API responses
- **Callback History**: Track all callback invocations with timestamps and status

### Improved
- Better exception handling in external API calls
- Graceful degradation when API keys are missing
- P&L calculation now includes percentage changes
- Health check endpoints for Kubernetes/container orchestration
- Telegram webhook error handling

### Fixed
- Missing pnl_percentage in `/mysilver` response
- Incomplete `/mysilver` response on line 108

## [1.0.0] - Initial Release

### Features
- Real-time silver price fetching (XAG/USD)
- Automatic INR parity calculation
- Personal portfolio P&L tracking
- Market score & bias analysis
- Telegram bot integration
- Economic calendar monitoring (worker service)
