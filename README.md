# Yellow Tracker Bot - Deployment Guide

## What This Is

A conversational AI financial assistant that runs on Telegram. It can:
- Track expenses and income naturally
- Manage investment portfolio (stocks, crypto, etc.)
- Log investment activity (buys, sells, dividends, staking rewards)
- Remember your preferences and patterns
- Answer questions about your finances
- Process voice messages and receipt photos

## Setup Instructions

### 1. Get Your API Keys

You need these keys (you already have most of them):

| Key | Where to get it |
|-----|-----------------|
| `TELEGRAM_BOT_TOKEN` | BotFather on Telegram |
| `CLAUDE_API_KEY` | console.anthropic.com |
| `GROQ_API_KEY` | console.groq.com |
| `AIRTABLE_API_KEY` | airtable.com/create/tokens |
| `AIRTABLE_BASE_ID` | From your Airtable URL (starts with 'app') |

### 2. Deploy on Railway (Recommended)

Railway is free for small projects and easy to use.

1. Go to [railway.app](https://railway.app) and sign up
2. Click "New Project" → "Deploy from GitHub repo"
3. Connect your GitHub and create a new repo
4. Upload `bot.py` and `requirements.txt` to the repo
5. In Railway, go to your project → "Variables"
6. Add these environment variables:
   - `TELEGRAM_BOT_TOKEN` = your token
   - `CLAUDE_API_KEY` = your key
   - `GROQ_API_KEY` = your key
   - `AIRTABLE_API_KEY` = your key
   - `AIRTABLE_BASE_ID` = your base ID
7. Railway will auto-deploy!

### 3. Alternative: Deploy on Replit

1. Go to [replit.com](https://replit.com) and sign up
2. Create a new Python Repl
3. Upload `bot.py` and `requirements.txt`
4. Go to "Secrets" (lock icon) and add your environment variables
5. Click "Run"

### 4. Alternative: Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_BOT_TOKEN="your_token"
export CLAUDE_API_KEY="your_key"
export GROQ_API_KEY="your_key"
export AIRTABLE_API_KEY="your_key"
export AIRTABLE_BASE_ID="your_base_id"

# Run
python bot.py
```

## Airtable Setup

Make sure your Airtable base has these tables with these exact column names:

### Messages
- user_id (Single line text)
- role (Single select: user, assistant)
- content (Long text)
- timestamp (Date, include time)

### Transactions
- user_id (Single line text)
- Date (Date)
- Type (Single select: income, expense)
- Amount (Number)
- Currency (Single select: USD, EUR, COP, AED)
- Category (Single select: food, transport, housing, utilities, shopping, entertainment, health, travel, education, personal care, gifts, subscriptions, insurance, taxes, fees, business, family, pets, other expense, salary, freelance, business income, investments, rental income, gifts received, refunds, other income)
- Description (Long text)
- Payment Method (Single select: cash, transfer, credit card, debit card)
- Payment Source (Single line text)

### Holdings
- user_id (Single line text)
- asset_type (Single select: stock, crypto, etf, bond, commodity, real estate, other)
- ticker (Single line text)
- name (Single line text)
- shares (Number, decimal)
- avg_cost (Number, decimal)
- currency (Single select: USD, EUR, COP, AED)
- platform (Single line text)
- notes (Long text)
- last_updated (Date, include time)

### Investment Activity
- user_id (Single line text)
- date (Date)
- activity_type (Single select: buy, sell, dividend, interest, staking reward, lending income, airdrop, transfer in, transfer out, fee, other)
- ticker (Single line text)
- shares (Number, decimal)
- price_per_unit (Number, decimal)
- total_amount (Number, decimal)
- currency (Single select: USD, EUR, COP, AED)
- platform (Single line text)
- realized_gain (Number, decimal)
- notes (Long text)

### Memory
- user_id (Single line text)
- fact (Long text)
- category (Single select: preference, pattern, personal, financial)
- created_at (Date, include time)

## Usage Examples

Once deployed, talk to your bot naturally:

**Expenses:**
- "spent $30 on lunch"
- "uber to airport 45 AED"
- "that was with my Amex"
- "actually it was $35"

**Investments:**
- "I own 50 shares of Google at $150 average"
- "bought 0.5 BTC at $60000 on Coinbase"
- "sold 10 NVDA at $900"
- "got $50 dividend from Apple"
- "earned 0.01 ETH from staking"

**Questions:**
- "how much did I spend this week?"
- "what's in my portfolio?"
- "show me my food expenses this month"
- "what dividends did I get this year?"

**Memory:**
- "remember that my primary card is Chase Sapphire"
- "I get paid on the 1st of every month"

The bot will learn and adapt to you over time!
