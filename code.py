import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from pymongo import MongoClient
import logging
import re
WEBHOOK_URL = "https://codereaper-t8q5.onrender.com"
# Set up logging to track errors and bot behavior
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
client = MongoClient("mongodb+srv://foodie:foodie123@cluster0.p99goy7.mongodb.net/")  # Replace with your MongoDB URI
db = client['code_database']
collection = db['code_snippets']

# Function to store a code snippet in the database
def store_code(function_name, arguments, language, code):
    logger.info(f"Storing code: {function_name}, {arguments}, {language}, {code}")
    collection.insert_one({
        "function_name": function_name,
        "arguments": arguments,
        "language": language,
        "code": code
    })

# Function to search for a code snippet in the database
def search_code(function_name, arguments):
    # Normalize the arguments to ensure consistent searching
    normalized_arguments = ' '.join(arguments.split()).strip()
    result = collection.find_one({
        "function_name": function_name,
        "arguments": normalized_arguments
    })
    
    if result:
        logger.info(f"Found code for {function_name}({arguments})")
        return f"Code in {result['language']}:\n{result['code']}"
    else:
        logger.info(f"No code found for {function_name}({arguments})")
        return "No matching code found."

# Handler to store code through the bot with /add command
async def add_code(update: Update, context: CallbackContext):
    try:
        # Extract the message text and split it using '|'
        user_input = update.message.text.split('|')
        
        # Log the user input to verify what's being sent
        logger.info(f"User input: {user_input}")
        
        # Ensure there are exactly 5 parts (command + function_name + arguments + language + code)
        if len(user_input) != 5:
            await update.message.reply_text("Invalid format. Please use the format: /add | function_name | arguments | language | code")
            return
        
        function_name = user_input[1].strip()
        arguments = user_input[2].strip()
        language = user_input[3].strip()
        code = user_input[4].strip()

        # Log the parsed values
        logger.info(f"Parsed values: function_name={function_name}, arguments={arguments}, language={language}, code={code}")
        
        # Store the code in the database
        store_code(function_name, arguments, language, code)
        await update.message.reply_text(f"Code for {function_name}({arguments}) added successfully.")
    
    except Exception as e:
        logger.error(f"Error occurred while adding code: {e}")
        await update.message.reply_text(f"An error occurred while processing your request: {e}")

# Handler to search for code through the bot with /search command
# Handler to search for code through the bot with /search command
async def search(update: Update, context: CallbackContext):
    try:
        # Split the user input to extract function name and arguments
        user_input = update.message.text.split(maxsplit=1)
        if len(user_input) < 2:
            await update.message.reply_text("Invalid format. Use: /search function_name arguments")
            return

        # Extract the function name and arguments
        function_name = user_input[1].split(' ', 1)[0]
        arguments = user_input[1].split(' ', 1)[1] if ' ' in user_input[1] else ''

        # Log the search parameters
        logger.info(f"Searching for function_name: {function_name} with arguments: {arguments}")
        
        # Search for the code in the database
        code = search_code(function_name, arguments)
        
        # Reply with the code
        await update.message.reply_text(code)

        # Send the secret voice message instead of an audio file
        audio_path = './audio.mp3'  # Replace with the correct path to your audio file
        with open(audio_path, 'rb') as voice_file:
            await update.message.reply_voice(voice_file)

    except Exception as e:
        logger.error(f"Error in search handler: {e}")
        await update.message.reply_text("An error occurred while searching for the code.")


# New handler to automatically detect and store code snippets
# New handler to automatically detect and store code snippets
async def detect_and_store_code(update: Update, context: CallbackContext):
    try:
        # Regular expression to match code that starts with includes, followed by function definition
        pattern = r"([\s\S]*?)\b(\w+)\s+(\w+)\((.*?)\)\s*\{([\s\S]*)\}"

        match = re.match(pattern, update.message.text)

        if match:
            # Extract the include statements, return type, function name, arguments, and code body
            includes = match.group(1).strip()
            return_type = match.group(2)
            function_name = match.group(3)
            arguments = match.group(4).strip()
            code_body = match.group(5).strip()

            # Construct the full code, including libraries, function signature, and body
            full_code = f"{includes}\n{return_type} {function_name}({arguments}) {{\n{code_body}\n}}"

            # Log the detected values
            logger.info(f"Detected code: includes={includes}, function_name={function_name}, arguments={arguments}, full_code={full_code}")

            # Store the full function in the database (default language is C++)
            store_code(function_name, arguments, "C++", full_code)

            # Reply to the user that the code was added successfully
            await update.message.reply_text(f"Code for {function_name}({arguments}) added successfully.")
        else:
            await update.message.reply_text("Could not detect a valid function signature. Please use /add to manually add code.")
    except Exception as e:
        logger.error(f"Error occurred while detecting and storing code: {e}")
        await update.message.reply_text(f"An error occurred while processing your request: {e}")


# Handler for errors
def error(update: Update, context: CallbackContext):
    logger.warning(f"Update {update} caused error {context.error}")

# Main function to start the bot
def main():
    # Telegram bot token
    TOKEN = '7387835703:AAEzh1ZhUrfwDlB_8HGJAeiTIdfHjN0EOT8'  # Replace with your bot token
    
    # Initialize the Application with a custom request timeout
    application = Application.builder().token(TOKEN).read_timeout(20).connect_timeout(20).build()

    # Commands
    application.add_handler(CommandHandler('add', add_code))   # For adding new code
    application.add_handler(CommandHandler('search', search))  # For searching code
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), detect_and_store_code))  # Auto-detect code snippets

    # Log all errors
    application.add_error_handler(error)

    # Start the bot using Webhook
    application.run_webhook(
        listen="0.0.0.0",  # Listen on all available interfaces
        port=int(os.environ.get("PORT", 8443)),  # Use PORT environment variable (default 8443)
        url_path=f"{TOKEN}",  # URL path for security
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"  # Full Webhook URL
    )

if __name__ == '__main__':
    main()

