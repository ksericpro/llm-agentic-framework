from langchain_core.prompts import ChatPromptTemplate
from logger_config import setup_logger

logger = setup_logger("translation")

class TranslationAgent:
    """
    Agent specialized in language translation.
    """
    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Translation Agent. 
            Your task is to translate the provided text into the target language while maintaining the original meaning, tone, and cultural nuances.
            
            **Rules:**
            1. Provide ONLY the translated text.
            2. Do not add explanations or notes unless the original text is ambiguous.
            3. Maintain markdown formatting if present in the source text.
            """),
            ("human", "Translate the following text into {target_language}:\n\n{text}")
        ])
        self.chain = self.prompt | self.llm

    def translate(self, text: str, target_language: str = "Chinese") -> str:
        """
        Translates text to the target language.
        """
        logger.info(f"Translating text to {target_language}...")
        print(f"      [TRANSLATOR] 🈯 Translating to {target_language}...")
        
        try:
            response = self.chain.invoke({
                "text": text,
                "target_language": target_language
            })
            translation = response.content.strip()
            logger.info("✅ Translation complete")
            print(f"      [TRANSLATOR] ✅ Translation successful ({len(translation)} chars).")
            return translation
        except Exception as e:
            logger.error(f"Translation error: {e}")
            print(f"      [TRANSLATOR] ❌ Translation failed: {e}")
            return f"Error during translation: {str(e)}"
