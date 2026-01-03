import os
import json
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pyairtable import Api

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION - Replace these with your actual keys
# =============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "YOUR_CLAUDE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "YOUR_AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "YOUR_AIRTABLE_BASE_ID")

# Airtable table names
TABLE_MESSAGES = "Messages"
TABLE_TRANSACTIONS = "Transactions"
TABLE_HOLDINGS = "Holdings"
TABLE_INVESTMENT_ACTIVITY = "Investment Activity"
TABLE_MEMORY = "Memory"

# =============================================================================
# AIRTABLE CLIENT
# =============================================================================
class AirtableClient:
    def __init__(self):
        self.api = Api(AIRTABLE_API_KEY)
        self.base = self.api.base(AIRTABLE_BASE_ID)
    
    def get_table(self, table_name):
        return self.base.table(table_name)
    
    # Messages
    def save_message(self, user_id: str, role: str, content: str):
        table = self.get_table(TABLE_MESSAGES)
        table.create({
            "user_id": str(user_id),
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_messages(self, user_id: str, limit: int = 50) -> list:
        table = self.get_table(TABLE_MESSAGES)
        records = table.all(
            formula=f"{{user_id}} = '{user_id}'",
            sort=["-timestamp"]
        )
        # Return in chronological order (oldest first)
        return list(reversed(records[:limit]))
    
    # Transactions
    def create_transaction(self, user_id: str, data: dict) -> str:
        table = self.get_table(TABLE_TRANSACTIONS)
        record = table.create({
            "user_id": str(user_id),
            "Date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
            "Type": data.get("type"),
            "Amount": data.get("amount"),
            "Currency": data.get("currency", "USD"),
            "Category": data.get("category"),
            "Description": data.get("description"),
            "Payment Method": data.get("payment_method"),
            "Payment Source": data.get("payment_source")
        })
        return record["id"]
    
    def update_transaction(self, record_id: str, data: dict):
        table = self.get_table(TABLE_TRANSACTIONS)
        update_fields = {}
        if "date" in data: update_fields["Date"] = data["date"]
        if "type" in data: update_fields["Type"] = data["type"]
        if "amount" in data: update_fields["Amount"] = data["amount"]
        if "currency" in data: update_fields["Currency"] = data["currency"]
        if "category" in data: update_fields["Category"] = data["category"]
        if "description" in data: update_fields["Description"] = data["description"]
        if "payment_method" in data: update_fields["Payment Method"] = data["payment_method"]
        if "payment_source" in data: update_fields["Payment Source"] = data["payment_source"]
        table.update(record_id, update_fields)
    
    def delete_transaction(self, record_id: str):
        table = self.get_table(TABLE_TRANSACTIONS)
        table.delete(record_id)
    
    def get_transactions(self, user_id: str, days: int = 90) -> list:
        table = self.get_table(TABLE_TRANSACTIONS)
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        records = table.all(
            formula=f"AND({{user_id}} = '{user_id}', {{Date}} >= '{cutoff}')",
            sort=["-Date"]
        )
        return records
    
    def get_recent_transaction(self, user_id: str) -> Optional[dict]:
        table = self.get_table(TABLE_TRANSACTIONS)
        records = table.all(
            formula=f"{{user_id}} = '{user_id}'",
            sort=["-Date"],
            max_records=1
        )
        return records[0] if records else None
    
    # Holdings
    def create_holding(self, user_id: str, data: dict) -> str:
        table = self.get_table(TABLE_HOLDINGS)
        record = table.create({
            "user_id": str(user_id),
            "asset_type": data.get("asset_type"),
            "ticker": data.get("ticker"),
            "name": data.get("name"),
            "shares": data.get("shares"),
            "avg_cost": data.get("avg_cost"),
            "currency": data.get("currency", "USD"),
            "platform": data.get("platform"),
            "notes": data.get("notes"),
            "last_updated": datetime.now().isoformat()
        })
        return record["id"]
    
    def update_holding(self, record_id: str, data: dict):
        table = self.get_table(TABLE_HOLDINGS)
        update_fields = {"last_updated": datetime.now().isoformat()}
        if "shares" in data: update_fields["shares"] = data["shares"]
        if "avg_cost" in data: update_fields["avg_cost"] = data["avg_cost"]
        if "platform" in data: update_fields["platform"] = data["platform"]
        if "notes" in data: update_fields["notes"] = data["notes"]
        table.update(record_id, update_fields)
    
    def delete_holding(self, record_id: str):
        table = self.get_table(TABLE_HOLDINGS)
        table.delete(record_id)
    
    def get_holdings(self, user_id: str) -> list:
        table = self.get_table(TABLE_HOLDINGS)
        return table.all(formula=f"{{user_id}} = '{user_id}'")
    
    def get_holding_by_ticker(self, user_id: str, ticker: str) -> Optional[dict]:
        table = self.get_table(TABLE_HOLDINGS)
        records = table.all(
            formula=f"AND({{user_id}} = '{user_id}', UPPER({{ticker}}) = '{ticker.upper()}')",
            max_records=1
        )
        return records[0] if records else None
    
    # Investment Activity
    def create_activity(self, user_id: str, data: dict) -> str:
        table = self.get_table(TABLE_INVESTMENT_ACTIVITY)
        record = table.create({
            "user_id": str(user_id),
            "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
            "activity_type": data.get("activity_type"),
            "ticker": data.get("ticker"),
            "shares": data.get("shares"),
            "price_per_unit": data.get("price_per_unit"),
            "total_amount": data.get("total_amount"),
            "currency": data.get("currency", "USD"),
            "platform": data.get("platform"),
            "realized_gain": data.get("realized_gain"),
            "notes": data.get("notes")
        })
        return record["id"]
    
    def get_activities(self, user_id: str, days: int = 365) -> list:
        table = self.get_table(TABLE_INVESTMENT_ACTIVITY)
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        records = table.all(
            formula=f"AND({{user_id}} = '{user_id}', {{date}} >= '{cutoff}')",
            sort=["-date"]
        )
        return records
    
    # Memory
    def save_memory(self, user_id: str, fact: str, category: str):
        table = self.get_table(TABLE_MEMORY)
        table.create({
            "user_id": str(user_id),
            "fact": fact,
            "category": category,
            "created_at": datetime.now().isoformat()
        })
    
    def get_memories(self, user_id: str) -> list:
        table = self.get_table(TABLE_MEMORY)
        return table.all(formula=f"{{user_id}} = '{user_id}'")
    
    def delete_memory(self, record_id: str):
        table = self.get_table(TABLE_MEMORY)
        table.delete(record_id)


# =============================================================================
# CLAUDE CLIENT
# =============================================================================
class ClaudeClient:
    def __init__(self):
        self.api_key = CLAUDE_API_KEY
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    async def send_message(self, messages: list, system_prompt: str, image_data: Optional[str] = None) -> dict:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Build the user message content
        if image_data:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data
                    }
                },
                {"type": "text", "text": messages[-1]["content"]}
            ]
            messages[-1]["content"] = content
        
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": messages
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()


# =============================================================================
# GROQ CLIENT (Voice Transcription)
# =============================================================================
class GroqClient:
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.base_url = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    async def transcribe(self, audio_data: bytes) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        files = {
            "file": ("audio.ogg", audio_data, "audio/ogg"),
            "model": (None, "whisper-large-v3")
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.base_url, headers=headers, files=files)
            response.raise_for_status()
            return response.json()["text"]


# =============================================================================
# PRICE FETCHER
# =============================================================================
class PriceFetcher:
    @staticmethod
    async def get_stock_price(ticker: str) -> Optional[float]:
        """Fetch stock price from a free API"""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                data = response.json()
                return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        except:
            return None
    
    @staticmethod
    async def get_crypto_price(ticker: str) -> Optional[float]:
        """Fetch crypto price from CoinGecko"""
        try:
            # Map common tickers to CoinGecko IDs
            ticker_map = {
                "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
                "ADA": "cardano", "DOT": "polkadot", "LINK": "chainlink",
                "MATIC": "matic-network", "AVAX": "avalanche-2",
                "USDT": "tether", "USDC": "usd-coin"
            }
            coin_id = ticker_map.get(ticker.upper(), ticker.lower())
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                data = response.json()
                return data[coin_id]["usd"]
        except:
            return None


# =============================================================================
# MAIN BOT
# =============================================================================
class YellowTrackerBot:
    def __init__(self):
        self.db = AirtableClient()
        self.claude = ClaudeClient()
        self.groq = GroqClient()
        self.price_fetcher = PriceFetcher()
    
    def build_system_prompt(self, user_id: str, transactions: list, holdings: list, 
                           activities: list, memories: list) -> str:
        """Build the system prompt with all user context"""
        
        # Format transactions
        transactions_text = "No recent transactions."
        if transactions:
            tx_lines = []
            for tx in transactions[:30]:  # Last 30 transactions
                f = tx["fields"]
                tx_lines.append(f"- {f.get('Date')}: {f.get('Type')} {f.get('Amount')} {f.get('Currency')} - {f.get('Category')} - {f.get('Description')} (Payment: {f.get('Payment Method')} {f.get('Payment Source') or ''}) [ID: {tx['id']}]")
            transactions_text = "\n".join(tx_lines)
        
        # Format holdings
        holdings_text = "No holdings."
        if holdings:
            h_lines = []
            for h in holdings:
                f = h["fields"]
                h_lines.append(f"- {f.get('ticker')} ({f.get('asset_type')}): {f.get('shares')} units @ avg {f.get('avg_cost')} {f.get('currency')} on {f.get('platform')} [ID: {h['id']}]")
            holdings_text = "\n".join(h_lines)
        
        # Format activities
        activities_text = "No recent investment activity."
        if activities:
            a_lines = []
            for a in activities[:20]:
                f = a["fields"]
                a_lines.append(f"- {f.get('date')}: {f.get('activity_type')} {f.get('shares')} {f.get('ticker')} @ {f.get('price_per_unit')} = {f.get('total_amount')} {f.get('currency')}")
            activities_text = "\n".join(a_lines)
        
        # Format memories
        memories_text = "No stored memories yet."
        if memories:
            m_lines = [f"- [{m['fields'].get('category')}] {m['fields'].get('fact')}" for m in memories]
            memories_text = "\n".join(m_lines)
        
        return f"""You are Yellow Tracker, a personal AI financial assistant. You help the user track their expenses, income, investments, and overall financial life through natural conversation.

## YOUR CAPABILITIES
You can:
1. Log expenses and income (transactions)
2. Update or delete previous transactions
3. Track investment holdings (stocks, crypto, ETFs, bonds, etc.)
4. Log investment activity (buys, sells, dividends, staking rewards, interest, etc.)
5. Answer questions about spending, portfolio, trends
6. Remember facts and preferences about the user
7. Provide financial insights and summaries

## USER'S FINANCIAL STATE

### Recent Transactions (expenses/income):
{transactions_text}

### Investment Holdings:
{holdings_text}

### Recent Investment Activity:
{activities_text}

### Memories (things you know about this user):
{memories_text}

## HOW TO RESPOND

You must ALWAYS respond with valid JSON in this exact format:
{{
  "actions": [
    {{
      "type": "create_transaction" | "update_transaction" | "delete_transaction" | "create_holding" | "update_holding" | "delete_holding" | "create_activity" | "save_memory" | "none",
      "data": {{ ... relevant fields ... }},
      "record_id": "only for updates/deletes"
    }}
  ],
  "response": "Your natural conversational response to the user"
}}

### Action Types and Data:

**create_transaction**: {{type, amount, currency, category, description, payment_method, payment_source, date}}
**update_transaction**: {{record_id required, plus any fields to update}}
**delete_transaction**: {{record_id required}}
**create_holding**: {{asset_type, ticker, name, shares, avg_cost, currency, platform, notes}}
**update_holding**: {{record_id required, plus any fields to update}}
**delete_holding**: {{record_id required}}
**create_activity**: {{activity_type, ticker, shares, price_per_unit, total_amount, currency, platform, realized_gain, notes, date}}
**save_memory**: {{fact, category: preference|pattern|personal|financial}}
**none**: No action needed, just responding

### Categories for Transactions:
Expenses: food, transport, housing, utilities, shopping, entertainment, health, travel, education, personal care, gifts, subscriptions, insurance, taxes, fees, business, family, pets, other expense
Income: salary, freelance, business income, investments, rental income, gifts received, refunds, other income

### Activity Types:
buy, sell, dividend, interest, staking reward, lending income, airdrop, transfer in, transfer out, fee, other

### Asset Types:
stock, crypto, etf, bond, commodity, real estate, other

## IMPORTANT BEHAVIORS

1. **Be conversational**: Respond naturally, not robotically.
2. **Infer intelligently**: If user says "that was with my Amex", understand they're updating the last transaction.
3. **Use context**: Reference past transactions and holdings when relevant.
4. **Ask for clarification** when truly needed, but make reasonable assumptions when you can.
5. **Remember things**: If user mentions something worth remembering (preferences, recurring expenses, etc.), save it to memory.
6. **Multiple actions**: You can perform multiple actions in one response if needed.
7. **Currency handling**: User's currencies are USD, EUR, COP, AED. Default to USD if unclear.
8. **European decimals**: 31,50 means 31.50

Current date: {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""

    async def process_message(self, user_id: str, user_message: str, image_data: Optional[str] = None):
        """Process an incoming message and return the response"""
        
        # Load user context
        messages_history = self.db.get_messages(str(user_id), limit=50)
        transactions = self.db.get_transactions(str(user_id))
        holdings = self.db.get_holdings(str(user_id))
        activities = self.db.get_activities(str(user_id))
        memories = self.db.get_memories(str(user_id))
        
        # Build system prompt
        system_prompt = self.build_system_prompt(
            str(user_id), transactions, holdings, activities, memories
        )
        
        # Build messages for Claude
        claude_messages = []
        for msg in messages_history:
            claude_messages.append({
                "role": msg["fields"]["role"],
                "content": msg["fields"]["content"]
            })
        
        # Add current message
        message_content = user_message
        if image_data:
            message_content = f"[User sent an image]\n\n{user_message if user_message else 'Please extract transaction data from this receipt/image.'}"
        
        claude_messages.append({
            "role": "user",
            "content": message_content
        })
        
        # Save user message to history
        self.db.save_message(str(user_id), "user", message_content)
        
        # Call Claude
        try:
            response = await self.claude.send_message(claude_messages, system_prompt, image_data)
            assistant_text = response["content"][0]["text"]
            
            # Parse Claude's response
            try:
                parsed = json.loads(assistant_text)
                actions = parsed.get("actions", [])
                response_text = parsed.get("response", "Done!")
                
                # Execute actions
                for action in actions:
                    await self.execute_action(str(user_id), action)
                
            except json.JSONDecodeError:
                # Claude didn't return valid JSON, use raw response
                response_text = assistant_text
            
            # Save assistant response to history
            self.db.save_message(str(user_id), "assistant", response_text)
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    async def execute_action(self, user_id: str, action: dict):
        """Execute a single action"""
        action_type = action.get("type")
        data = action.get("data", {})
        record_id = action.get("record_id")
        
        try:
            if action_type == "create_transaction":
                self.db.create_transaction(user_id, data)
            
            elif action_type == "update_transaction":
                if record_id:
                    self.db.update_transaction(record_id, data)
            
            elif action_type == "delete_transaction":
                if record_id:
                    self.db.delete_transaction(record_id)
            
            elif action_type == "create_holding":
                # Check if holding already exists
                existing = self.db.get_holding_by_ticker(user_id, data.get("ticker", ""))
                if existing:
                    # Update existing holding
                    self.db.update_holding(existing["id"], data)
                else:
                    self.db.create_holding(user_id, data)
            
            elif action_type == "update_holding":
                if record_id:
                    self.db.update_holding(record_id, data)
            
            elif action_type == "delete_holding":
                if record_id:
                    self.db.delete_holding(record_id)
            
            elif action_type == "create_activity":
                self.db.create_activity(user_id, data)
                
                # Also update the holding if it's a buy/sell
                if data.get("activity_type") in ["buy", "sell"]:
                    await self.update_holding_from_activity(user_id, data)
            
            elif action_type == "save_memory":
                self.db.save_memory(user_id, data.get("fact", ""), data.get("category", "personal"))
            
        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}")
    
    async def update_holding_from_activity(self, user_id: str, activity_data: dict):
        """Update holding when a buy/sell activity is logged"""
        ticker = activity_data.get("ticker")
        if not ticker:
            return
        
        existing = self.db.get_holding_by_ticker(user_id, ticker)
        shares_change = activity_data.get("shares", 0)
        price = activity_data.get("price_per_unit", 0)
        
        if activity_data.get("activity_type") == "buy":
            if existing:
                # Calculate new average cost
                old_shares = existing["fields"].get("shares", 0)
                old_avg = existing["fields"].get("avg_cost", 0)
                new_shares = old_shares + shares_change
                new_avg = ((old_shares * old_avg) + (shares_change * price)) / new_shares if new_shares > 0 else 0
                self.db.update_holding(existing["id"], {"shares": new_shares, "avg_cost": new_avg})
            else:
                # Create new holding
                self.db.create_holding(user_id, {
                    "asset_type": activity_data.get("asset_type", "stock"),
                    "ticker": ticker,
                    "shares": shares_change,
                    "avg_cost": price,
                    "currency": activity_data.get("currency", "USD"),
                    "platform": activity_data.get("platform")
                })
        
        elif activity_data.get("activity_type") == "sell":
            if existing:
                old_shares = existing["fields"].get("shares", 0)
                new_shares = old_shares - shares_change
                if new_shares <= 0:
                    self.db.delete_holding(existing["id"])
                else:
                    self.db.update_holding(existing["id"], {"shares": new_shares})


# =============================================================================
# TELEGRAM HANDLERS
# =============================================================================
bot = YellowTrackerBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome = """👋 Hey! I'm Yellow Tracker, your personal finance assistant.

Just talk to me naturally about your money:

💰 **Expenses & Income**
"spent $30 on lunch"
"got paid $5000 salary"
"that was with my Chase card"

📈 **Investments**
"I bought 10 shares of Apple at $180"
"I own 0.5 BTC"
"sold half my Tesla"

📊 **Questions**
"how much did I spend on food this week?"
"what's my portfolio worth?"
"show me my recent transactions"

I'll remember everything and learn your preferences over time. Let's go!"""
    
    await update.message.reply_text(welcome)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    text = update.message.text
    
    response = await bot.process_message(user_id, text)
    await update.message.reply_text(response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    user_id = update.effective_user.id
    
    # Download voice file
    voice_file = await update.message.voice.get_file()
    voice_data = await voice_file.download_as_bytearray()
    
    # Transcribe
    try:
        transcription = await bot.groq.transcribe(bytes(voice_data))
        response = await bot.process_message(user_id, transcription)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        await update.message.reply_text("Sorry, I couldn't process that voice message. Please try again.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    user_id = update.effective_user.id
    caption = update.message.caption or ""
    
    # Get the highest resolution photo
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_data = await photo_file.download_as_bytearray()
    
    # Convert to base64
    image_base64 = base64.b64encode(bytes(photo_data)).decode('utf-8')
    
    response = await bot.process_message(user_id, caption, image_base64)
    await update.message.reply_text(response)

def main():
    """Start the bot"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Start polling
    logger.info("Starting Yellow Tracker bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
