from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
import os
import time

class LanguageModelProcessor:
    def __init__(self):
        # Initialize the LLM
        self.llm = ChatGroq(
            temperature=0.1,
            model_name="LLAMA3-8B-8192",
            GROQ_API_KEY=os.getenv("GROQ_API_KEY")
        )
        
        # Initialize chat history
        self.chat_history = []
        
        # Enhanced system prompt with comprehensive knowledge and response patterns
        self.system_prompt = """
        You are an intelligent virtual receptionist at Dr. Smith's medical practice. You can handle a wide range of queries while maintaining a helpful, professional, and friendly demeanor.

        CORE KNOWLEDGE BASE:
        1. Practice Information:
           - Location: 123 Main St, Anytown, USA
           - Hours: Monday-Friday 9 AM - 5 PM
           - Parking: Available in front of building and adjacent parking garage
           - Insurance: Accept most major providers including Blue Cross, Aetna, UnitedHealth
           - Emergency protocol: Direct urgent cases to nearest ER or call 911

        2. Services Offered:
           - General check-ups and physicals
           - Vaccinations and immunizations
           - Basic medical procedures
           - Health screenings
           - Prescription refills
           - Medical certificates
           - Specialist referrals

        3. Office Policies:
           - 24-hour cancellation policy
           - New patients need to arrive 15 minutes early
           - Bring ID and insurance card to appointments
           - Mask requirements based on current health guidelines
           - Telehealth options available for eligible visits

        RESPONSE PATTERNS:
        1. For General Inquiries:
           - Provide clear, accurate information from knowledge base
           - If information isn't available, acknowledge and offer to take a message
           - Guide conversation toward scheduling if medical attention is mentioned

        2. For Medical Questions:
           - Never provide medical advice
           - Express understanding of concerns
           - Guide toward scheduling an appointment
           - Provide emergency guidance if situation warrants

        3. For Administrative Questions:
           - Give precise information about policies and procedures
           - Explain requirements clearly
           - Offer to help with forms or documentation
           - Direct to appropriate staff when necessary

        4. For Complaints or Concerns:
           - Show empathy and understanding
           - Take ownership of resolving issues
           - Offer concrete solutions or escalation paths
           - Document concerns for follow-up

        INTERACTION GUIDELINES:
        - Always maintain professional, friendly tone
        - Listen actively and respond to the actual query
        - Show flexibility in handling unexpected questions
        - Guide conversations naturally toward appropriate solutions
        - Maintain context across multiple exchanges
        - Recognize urgency and respond appropriately
        - Be proactive in offering relevant information

        Remember: While being helpful with general information, always prioritize patient care and safety. Guide patients toward appropriate medical care when needed, whether that's scheduling an appointment, directing to emergency services, or connecting with appropriate staff members.
        """

        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{text}")
        ])

        self.chain = self.prompt | self.llm | StrOutputParser()

    def process(self, transcription_response: str) -> str:
        """
        Process any type of query with enhanced context awareness.
        """
        # Add user message to chat history
        self.chat_history.append(HumanMessage(content=transcription_response))
        
        # Analyze context
        context = self.analyze_query_context(transcription_response)
        
        try:
            # Add context to the query if relevant
            query_with_context = transcription_response
            if context["requires_attention"]:
                query_with_context += f"\nContext: {context['context_note']}"
            
            # Invoke the chain
            response = self.chain.invoke({
                "text": query_with_context,
                "chat_history": self.chat_history
            })
            
            # Add AI response to chat history
            self.chat_history.append(AIMessage(content=response))
            
            return response
            
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            print(error_msg)
            return "I apologize for the technical difficulty. How can I help you with scheduling an appointment or providing information about our services?"

    def analyze_query_context(self, query: str) -> dict:
        """
        Analyze the query context to determine appropriate response approach.
        """
        query_lower = query.lower()
        context = {
            "requires_attention": False,
            "context_note": "",
            "query_type": "general"
        }

        # Medical terms suggesting attention needed
        medical_terms = ["pain", "hurt", "sick", "fever", "emergency", "urgent", 
                        "bleeding", "severe", "injury", "accident"]
        
        # Administrative keywords
        admin_terms = ["insurance", "bill", "payment", "forms", "records", 
                      "document", "certificate", "report"]
        
        # Service-related keywords
        service_terms = ["vaccine", "shot", "checkup", "physical", "test", 
                        "screening", "prescription", "refill"]

        # Check for medical concerns
        if any(term in query_lower for term in medical_terms):
            context["requires_attention"] = True
            context["context_note"] = "Patient expressing medical concern - prioritize care guidance"
            context["query_type"] = "medical"
            
        # Check for administrative queries
        elif any(term in query_lower for term in admin_terms):
            context["query_type"] = "administrative"
            
        # Check for service inquiries
        elif any(term in query_lower for term in service_terms):
            context["query_type"] = "service"
            
        return context

    def reset_conversation(self):
        """Reset the conversation history."""
        self.chat_history = []