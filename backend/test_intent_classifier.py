import sys
from pathlib import Path

# Add the parent directory to path to allow imports
sys.path.append(str(Path(__file__).parent))

from services.message_processor import AIIntentClassifier, IntentType
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_intent_result(message: str, result) -> None:
    """Print the classification results in a readable format."""
    print("\n" + "="*60)
    print(f"Message: {message}")
    print("-"*60)
    print(f"Detected Intent: {result.intent}")
    print(f"Confidence: {result.confidence:.2f}")
    print("\nExtracted Entities:")
    for key, value in result.entities.items():
        print(f"  {key}: {value}")
    if hasattr(result, 'needs_clarification') and result.needs_clarification and hasattr(result, 'clarification_prompt') and result.clarification_prompt:
        print(f"\n⚠️  Needs Clarification: {result.clarification_prompt}")
    print("="*60 + "\n")

def test_classifier_interactive():
    """Interactive test for the intent classifier."""
    print("Initializing AI Intent Classifier...")
    try:
        classifier = AIIntentClassifier()
        print("✅ Classifier initialized successfully!")
        print("\nType your messages to test intent classification.")
        print("Type 'exit' or press Ctrl+C to quit.\n")
        
        while True:
            try:
                message = input("\nYour message: ").strip()
                
                if message.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break
                    
                if not message:
                    print("Please enter a message or type 'exit' to quit.")
                    continue
                
                # Classify the intent
                result = classifier.detect_intent(message)
                print_intent_result(message, result)
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                print(f"❌ Error: {str(e)}")
                
    except Exception as e:
        logger.error("Failed to initialize classifier", exc_info=True)
        print(f"❌ Failed to initialize classifier: {str(e)}")
        return

if __name__ == "__main__":
    test_classifier_interactive()
